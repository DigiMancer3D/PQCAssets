#!/usr/bin/env python3
"""
pah_wrap_improved.py - Bulk PQC Asset Wrapper for PQCassets Project
Static Asset || Containerized PQC Zip-Style Storage

Wraps files or entire folders using Falcon, SPHINCS+, or Hybrid via the pah C binary.
Produces .pqcasset files or multi-asset containers.

This is the main recommended tool. The old pah_wrap.py can be archived.
"""
import argparse
import os
import sys
import subprocess
import hashlib
import base64
import json
import tempfile
import shutil
import getpass
import time
import string
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

# ==================== SEEDS INTEGRATION ====================
# Add seeds/ dir to path so user_secret, auto_seed, trinary_dowsing are importable
_script_dir = Path(__file__).resolve().parent
_seeds_dir = _script_dir / "seeds"
if _seeds_dir.is_dir():
    sys.path.insert(0, str(_seeds_dir))
# Now "from user_secret import ..." etc will work when seeds/ present.
# - auto_seed: default for general crypto randomness (e.g. instance names, salts)
# - user_secret: base when password provided for KDF
# - trinary_dowsing: custom high-density seed, activate with future --seed-mode trinary

DEFAULT_OUTPUT_DIR = Path("pqc_wrapped")
DEFAULT_ALGORITHM = "hybrid"
SUPPORTED_ALGORITHMS = ["falcon", "sphincs", "hybrid"]

PAH_BINARY = None


def generate_instance_name(prefix: str = "inst") -> str:
    import random
    import string
    chars = random.choices(string.ascii_lowercase + string.digits, k=6)
    return f"{prefix}_{''.join(chars)}"


def parse_human_size(size_str: str) -> int:
    size_str = size_str.strip().upper().replace(" ", "")
    multipliers = {
        'K': 1024, 'KB': 1024,
        'M': 1024**2, 'MB': 1024**2,
        'G': 1024**3, 'GB': 1024**3,
        'T': 1024**4, 'TB': 1024**4,
    }
    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[:-len(suffix)]) * mult)
            except ValueError:
                pass
    return int(size_str)


def make_unique_path(dir_path: Path, name: str) -> Path:
    """
    Auto-name to avoid collisions: if exists, append "_" + last 6 digits of epoch
    (the rapidly changing LSB side of unix timestamp). Used for privacy-cleaned names too.
    """
    p = dir_path / name
    if not p.exists():
        return p
    ts6 = str(int(time.time()))[-6:]
    if "." in name and not name.startswith("."):
        stem, suf = name.rsplit(".", 1)
        new_name = f"{stem}_{ts6}.{suf}"
    else:
        new_name = f"{name}_{ts6}"
    new_p = dir_path / new_name
    if new_p.exists():
        # extremely rare in same second: add short random
        extra = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        if "." in new_name:
            stem, suf = new_name.rsplit(".", 1)
            new_name = f"{stem}_{extra}.{suf}"
        else:
            new_name = f"{new_name}_{extra}"
        new_p = dir_path / new_name
    return new_p


def find_pah_binary() -> str:
    global PAH_BINARY
    if PAH_BINARY:
        return PAH_BINARY

    env_path = os.environ.get("PAH_BINARY")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists() and p.is_file() and os.access(p, os.X_OK):
            PAH_BINARY = str(p.resolve())
            return PAH_BINARY

    candidates = [
        Path.cwd() / "pah" / "pah",
        Path.cwd() / "bin" / "pah",
        Path.cwd().parent / "pah" / "pah",
        Path("pah") / "pah",
        Path("bin") / "pah",
        Path.home() / ".local" / "bin" / "pah",
        Path("/usr/local/bin/pah"),
        Path("/usr/bin/pah"),
    ]

    for c in candidates:
        if c.exists() and c.is_file() and os.access(c, os.X_OK):
            PAH_BINARY = str(c.resolve())
            return PAH_BINARY

    print("ERROR: pah binary not found.")
    print("Set PAH_BINARY env var or use --pah-binary /full/path/to/pah")
    sys.exit(1)


def run_pah(cmd: List[str], timeout: int = 120, cwd: str = None) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as e:
        return False, str(e)


def compute_content_hash(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


# ==================== SECURE WIPE / DELETE (shred/srm + wipe-before-shred + anti-journal) ====================

def secure_wipe(file_path: Path, passes: int = 1) -> bool:
    """Multi-pass random overwrite (better than fixed pattern) + fsync. Failsafe component."""
    try:
        if not file_path.exists() or not file_path.is_file():
            return False
        file_size = file_path.stat().st_size
        if file_size == 0:
            return True
        for _ in range(max(1, passes)):
            with open(file_path, "r+b") as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        return True
    except Exception as e:
        print(f"Warning: secure_wipe failed for {file_path.name}: {e}")
        return False


def secure_delete(file_path: Path, passes: int = 3) -> bool:
    """
    wipe-before-shred: best effort secure delete.
    - If shred available: pre-wipe + shred -n passes -z -u (handles journaling FS well)
    - Else if srm: pre-wipe + srm
    - Else: multi-pass random wipe + unlink (our failsafe)
    --keep-source callers MUST avoid calling this on originals.
    """
    if not file_path.exists() or not file_path.is_file():
        return False
    try:
        if shutil.which("shred"):
            secure_wipe(file_path, passes=1)  # wipe-before-shred
            cmd = ["shred", "-n", str(passes), "-z", "-u", str(file_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode == 0:
                return True
            print(f"shred non-zero exit: {res.stderr.strip()[:200]}")
        elif shutil.which("srm"):
            secure_wipe(file_path, passes=1)
            cmd = ["srm", "-v", str(file_path)]  # verbose; add -f if needed but srm usually non-interactive
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode == 0:
                return True
        # Fallback wipe + delete (anti-forensic enough for most)
        if secure_wipe(file_path, passes=passes):
            file_path.unlink(missing_ok=True)
            return True
        file_path.unlink(missing_ok=True)
        return False
    except Exception as e:
        print(f"Warning: secure_delete failed for {file_path.name}: {e}")
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
        return False


# keep old name as alias for any external calls
secure_wipe_and_delete = secure_delete


# ==================== PASSWORD HELPERS (CRYPTO REQUIRED) ====================

def check_crypto_for_password() -> None:
    """Enforce that cryptography is installed for any password-protected wrap/extract."""
    try:
        import cryptography
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        print("ERROR: 'cryptography' package is REQUIRED for all password-protected flows.")
        print("       Install with: pip install cryptography")
        print("       (This enables Fernet AES + strong salted PBKDF2 KDF)")
        sys.exit(1)


def derive_fernet_key(password: str, salt: Optional[bytes] = None) -> bytes:
    """
    Upgraded secure KDF (v2.9):
    - Base: user_secret.generate_user_secret_seed (SHA3-512 + SHAKE256) when password given
    - Layer: salted PBKDF2-HMAC-SHA256 (600k iters) over the base seed for greatly increased security
    - Fallback (no user_secret): improved salted SHA3 + shake
    - Random per-asset salt supported (stored in manifest header for decrypt)
    """
    if salt is None:
        salt = b"PQC-Scout-Knife-v2.9-kdf-fixed-salt"  # for old assets / fallback

    pw_bytes = password.encode("utf-8") if isinstance(password, str) else password

    # Layer 1: user_secret as base (preferred when pw provided)
    try:
        from user_secret import generate_user_secret_seed
        base_seed = generate_user_secret_seed(pw_bytes, output_len=32)
    except Exception:
        # Improved fallback (salted)
        h = hashlib.sha3_512(pw_bytes + salt).digest()
        base_seed = hashlib.shake_256(h).digest(32)

    # Layer 2: strong PBKDF2 (requires cryptography, which we checked)
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,  # OWASP-level strength, ~0.3-1s CPU
        )
        key_material = kdf.derive(base_seed)
    except Exception:
        # Last resort (shouldn't happen)
        key_material = hashlib.sha3_256(base_seed + salt).digest()

    return base64.urlsafe_b64encode(key_material)


def build_nested_wrapper_b(original_data: bytes, manifest: dict,
                           password: Optional[str] = None,
                           kdf_salt: Optional[bytes] = None) -> bytes:
    inner_manifest = manifest.copy()
    inner_manifest.update({
        "is_hidden_internal": True,
        "pah_wrapper_version": "2.9.0-phase1-secure-shred-kdf-seeds"
    })

    payload = original_data
    encrypted = False

    if password:
        check_crypto_for_password()
        if kdf_salt is None:
            kdf_salt = os.urandom(16)  # random salt per protected asset
            inner_manifest["kdf_salt_b64"] = base64.b64encode(kdf_salt).decode()
        else:
            inner_manifest["kdf_salt_b64"] = base64.b64encode(kdf_salt).decode()

        from cryptography.fernet import Fernet
        key = derive_fernet_key(password, salt=kdf_salt)
        f = Fernet(key)
        payload = f.encrypt(payload)
        encrypted = True

    wrapper_b = {
        "header": inner_manifest,
        "payload_encrypted": encrypted,
        "data_b64": base64.b64encode(payload).decode()
    }
    return json.dumps(wrapper_b, indent=2).encode("utf-8")


def prompt_for_password(reason: str = "protected asset") -> Optional[str]:
    try:
        val = getpass.getpass(f"🔐 Enter password for {reason} (input hidden): ")
        return val.strip() if val and val.strip() else None
    except (EOFError, KeyboardInterrupt):
        return None


def prompt_for_password_with_retries(reason: str = "protected asset", max_attempts: int = 3) -> Optional[str]:
    for attempt in range(1, max_attempts + 1):
        pw = prompt_for_password(reason)
        if pw:
            return pw
        if attempt < max_attempts:
            print(f"   Wrong or empty password (attempt {attempt}/{max_attempts}). Try again...")
        else:
            print(f"   All {max_attempts} attempts failed for {reason}.")
    return None


def try_decrypt_payload(data_b64: str, password: Optional[str], kdf_salt_b64: Optional[str] = None) -> Optional[bytes]:
    if not password:
        return None
    check_crypto_for_password()
    try:
        from cryptography.fernet import Fernet
        if kdf_salt_b64:
            kdf_salt = base64.b64decode(kdf_salt_b64)
        else:
            kdf_salt = b"PQC-Scout-Knife-v2.9-kdf-fixed-salt"  # compat for old no-salt assets
        key = derive_fernet_key(password, salt=kdf_salt)
        f = Fernet(key)
        return f.decrypt(base64.b64decode(data_b64))
    except Exception:
        return None


def resolve_password(pw_arg: Optional[str]) -> Optional[str]:
    if not pw_arg:
        return None
    p = Path(pw_arg).expanduser()
    if p.is_file() and p.suffix.lower() == ".json":
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key in ("password", "pw", "secret", "passphrase", "key"):
                    if key in data and str(data[key]).strip():
                        return str(data[key]).strip()
            elif isinstance(data, str) and data.strip():
                return data.strip()
            return pw_arg
        except Exception:
            print(f"⚠️  Could not parse password JSON {p.name} — treating as literal.")
    return pw_arg


# ==================== WRAPPING ====================

def wrap_single_file(input_path: Path, output_dir: Path, algorithm: str,
                     use_base64=False, add_hash=False, quiet=False,
                     embed_manifest: bool = True,
                     public_manifest: bool = False,
                     password: Optional[str] = None,
                     nested: bool = True) -> Optional[Path]:

    input_path = input_path.resolve()
    if not input_path.exists() or not input_path.is_file():
        if not quiet:
            print(f"ERROR: File not found: {input_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    original_data = input_path.read_bytes()

    original_stem = input_path.stem
    original_suffix = input_path.suffix
    base_stem = original_stem

    manifest = {
        "original_filename": input_path.name,
        "original_size": len(original_data),
        "wrapped_at": datetime.now(timezone.utc).isoformat() + "Z",
        "algorithm": algorithm,
        "base64_encoded": use_base64,
        "content_hash": None,
        "pah_wrapper_version": "2.9.0-phase1-secure-shred-kdf-seeds",
    }

    final_data = original_data
    if use_base64:
        final_data = base64.b64encode(original_data)

    if add_hash:
        content_hash = compute_content_hash(original_data)
        manifest["content_hash"] = content_hash
        hash_suffix = content_hash[:12]
        if original_suffix.lower() == ".pqcasset":
            base_name = f"{base_stem}_{hash_suffix}.pqcasset"
        else:
            base_name = f"{base_stem}_{hash_suffix}{original_suffix}"
    else:
        if original_suffix.lower() == ".pqcasset":
            base_name = f"{base_stem}.pqcasset"
        else:
            base_name = f"{input_path.name}.pqcasset"

    kdf_salt = None
    if password:
        kdf_salt = os.urandom(16)
        manifest["kdf_salt_b64"] = base64.b64encode(kdf_salt).decode()

    if nested and embed_manifest:
        nested_payload = build_nested_wrapper_b(original_data, manifest, password, kdf_salt)
        final_data = nested_payload
        if use_base64:
            final_data = base64.b64encode(final_data)

    temp_path = None
    if use_base64 or add_hash or (nested and embed_manifest):
        temp_path = output_dir / f".tmp_{input_path.name}"
        temp_path.write_bytes(final_data)
        input_path = temp_path

    output_path = make_unique_path(output_dir, base_name)
    success, _ = run_pah([find_pah_binary(), f"--wrap-{algorithm}", str(input_path), str(output_path)])

    if temp_path and temp_path.exists():
        temp_path.unlink()

    actual_path = output_path
    if success:
        if not output_path.exists():
            double_ext_path = output_path.with_name(output_path.name + ".pqcasset")
            if double_ext_path.exists():
                try:
                    if output_path.exists():
                        output_path.unlink()
                    double_ext_path.rename(output_path)
                    actual_path = output_path
                    if not quiet:
                        print("  (auto-cleaned double extension)")
                except Exception as e:
                    if not quiet:
                        print(f"  Warning: Could not auto-clean double ext ({e})")
                    actual_path = double_ext_path

    if success and actual_path.exists():
        if public_manifest:
            manifest_path = actual_path.parent / (actual_path.name + ".manifest.json")
            manifest_path.write_text(json.dumps(manifest, indent=2))

        if not quiet:
            lock_note = " (password protected)" if password else ""
            hidden_note = " [hidden internal manifest]" if embed_manifest else ""
            print(f"✅ Wrapped ({algorithm}){lock_note}{hidden_note}: {actual_path.name}")
        return actual_path

    if success and not quiet:
        print(f"WARNING: pah succeeded but output file not found at expected location.")
    return None


def wrap_folder_as_container(folder: Path, output_dir: Path, name: str, algorithm: str,
                             keep_temps: bool = False, quiet: bool = False,
                             password: Optional[str] = None,
                             keep_source: bool = False,
                             cleanup_archives: bool = True) -> Optional[Path]:
    """
    Note: cleanup_archives=True by default (no old archived folders left).
    keep_source=True: uses COPY not MOVE, disables all shred/delete of sources and archive cleanup.
    """

    folder = folder.resolve()
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    container_path = make_unique_path(output_dir, f"{name}.pqcasset")
    temp_dir = Path(tempfile.mkdtemp(prefix="pqc_prewrap_"))

    if not quiet:
        print(f"Creating PQC container '{name}' using algorithm={algorithm}")

    original_files = [f for f in folder.rglob("*") if f.is_file()]

    processing_dir = temp_dir / "processing_files"
    processing_dir.mkdir(parents=True, exist_ok=True)
    processing_files: List[Path] = []
    use_move = not keep_source   # if keep_source: COPY only, leave originals untouched, no shred later

    for f in original_files:
        dest = processing_dir / f.name
        try:
            if use_move:
                shutil.move(str(f), str(dest))
            else:
                shutil.copy2(str(f), str(dest))
            processing_files.append(dest)
        except Exception as e:
            if not quiet:
                print(f"  Warning: Could not process {f.name} ({e})")

    if not processing_files:
        print("No files to process. Aborting.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    prewrapped: List[Path] = []
    for i, f in enumerate(processing_files, 1):
        if not quiet:
            print(f"  [{i}/{len(processing_files)}] Pre-wrapping {f.name} ...", end=" ")

        use_hash = not f.suffix.lower().endswith(".pqcasset")
        wrapped = wrap_single_file(f, temp_dir, algorithm,
                                   use_base64=False, add_hash=use_hash, quiet=True,
                                   embed_manifest=True, public_manifest=False,
                                   password=password, nested=True)

        if wrapped:
            clean_name = wrapped.name
            if clean_name.lower().endswith(".pqcasset.pqcasset"):
                clean_name = clean_name[:-len(".pqcasset")]
            clean_path = temp_dir / clean_name
            if wrapped != clean_path:
                if clean_path.exists():
                    clean_path.unlink()
                shutil.move(str(wrapped), str(clean_path))
            prewrapped.append(clean_path)
            if not quiet:
                print("✓")
            # If we moved the original (not keep_source), securely shred the husk NOW
            # (content already used for wrapped version; prevents journal recovery of originals)
            if use_move:
                if not quiet:
                    print(f"    [shred original] {f.name} ...", end=" ")
                if secure_delete(f, passes=2):
                    if not quiet:
                        print("✓")
                else:
                    if not quiet:
                        print("(fallback wipe)")
        else:
            if not quiet:
                print("✗")

    if not prewrapped:
        # restore if failure (only the ones we moved)
        for pf in processing_files:
            if use_move:
                try:
                    shutil.move(str(pf), str(folder / pf.name))
                except Exception:
                    pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    success, _ = run_pah([find_pah_binary(), "--create-container", str(container_path)])
    if not success:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    temp_copies = []
    for clean_path in prewrapped:
        copy_path = Path.cwd() / clean_path.name
        shutil.copy(clean_path, copy_path)
        temp_copies.append(copy_path)

    added = 0
    for i, copy_path in enumerate(temp_copies, 1):
        success, _ = run_pah([find_pah_binary(), "--add-to-container", str(container_path), copy_path.name])
        if success:
            added += 1
            if not quiet:
                print(f"  + [{i}/{len(temp_copies)}] {copy_path.name} -> container")

    for p in temp_copies:
        if p.exists():
            p.unlink()

    if not keep_temps:
        shutil.rmtree(temp_dir, ignore_errors=True)

    if not keep_source and folder.exists():
        archive_dir = output_dir / "source_archives"
        archive_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"source_{folder.name}_{timestamp}"
        archive_path = archive_dir / archive_name

        try:
            shutil.move(str(folder), str(archive_path))
            if not quiet:
                print(f"  → Original source moved to: source_archives/{archive_name}/")

            if cleanup_archives:
                if not quiet:
                    print("  → Securely wiping archived source (default: no traces left)...")
                for f in list(archive_path.rglob("*")):
                    if f.is_file():
                        secure_delete(f, passes=1)
                # also nuke any empty subdir husks
                for d in sorted(archive_path.rglob("*"), key=lambda x: len(str(x)), reverse=True):
                    if d.is_dir():
                        try:
                            d.rmdir()
                        except Exception:
                            pass
                try:
                    if archive_path.exists():
                        archive_path.rmdir()
                except Exception:
                    pass
                if not quiet:
                    print("  → Archived source securely wiped and removed (anti-forensic).")
        except Exception as e:
            if not quiet:
                print(f"  Warning: Could not move source folder ({e})")

    if not quiet:
        print(f"\n✅ PQC Container created: {container_path}")
        print(f"   Entries: {added}")

    return container_path


# ==================== EXTRACTION ====================

def extract_wrapped_file(wrapped_path: Path, output_dir: Path, password: Optional[str] = None):
    wrapped_path = wrapped_path.resolve()
    if not wrapped_path.exists():
        print(f"ERROR: File not found: {wrapped_path}")
        return False

    if not verify_wrapped_file(wrapped_path):
        print("WARNING: Structural verification failed")

    with open(wrapped_path, "rb") as f:
        magic = f.read(4)
        if magic != b"PAH1":
            print("ERROR: Not a valid PAH file")
            return False
        sig_len = int.from_bytes(f.read(4), "little")
        data_len = int.from_bytes(f.read(4), "little")
        f.seek(12 + sig_len)
        raw_data = f.read(data_len)

    final_data = unwrap_pah_layers(raw_data)
    extracted_data = final_data
    original_name = wrapped_path.stem

    try:
        decoded = final_data.decode("utf-8", errors="ignore")
        wrapper_b = json.loads(decoded)

        if isinstance(wrapper_b, dict) and wrapper_b.get("header", {}).get("is_hidden_internal"):
            print("🔒 Hidden/internal manifest detected.")

            b64_data = wrapper_b.get("data_b64", "")
            header = wrapper_b.get("header", {})
            original_name = header.get("original_filename", original_name)

            if wrapper_b.get("payload_encrypted"):
                pw = password if password else None
                if not pw:
                    pw = prompt_for_password_with_retries(original_name, max_attempts=3)

                if pw:
                    kdf_salt_b64 = header.get("kdf_salt_b64")
                    decrypted = try_decrypt_payload(b64_data, pw, kdf_salt_b64)
                    if decrypted:
                        extracted_data = decrypted
                        print(f"✅ Unlocked successfully: {original_name}")
                    else:
                        print(f"❌ All 3 password attempts failed for protected asset: {original_name}")
                        print("   → Asset remains protected. Nothing written.")
                        return False
                else:
                    print(f"🔐 No password provided for protected asset: {original_name}")
                    print("   → Asset remains protected. Nothing written.")
                    return False
            else:
                extracted_data = base64.b64decode(b64_data) if b64_data else final_data
    except Exception:
        pass

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / original_name).write_bytes(extracted_data)
    print(f"✅ Extracted: {original_name} → {output_dir}")
    return True


def unwrap_pah_layers(data: bytes, max_depth: int = 5) -> bytes:
    depth = 0
    current_data = data
    while depth < max_depth:
        if len(current_data) < 12 or current_data[:4] != b"PAH1":
            break
        try:
            sig_len = int.from_bytes(current_data[4:8], "little")
            data_len = int.from_bytes(current_data[8:12], "little")
            if sig_len == 0 or data_len == 0:
                break
            current_data = current_data[12 + sig_len:12 + sig_len + data_len]
            depth += 1
        except Exception:
            break
    return current_data


def extract_from_container(container_path: Path, output_dir: Path, password: Optional[str] = None):
    container_path = container_path.resolve()
    if not container_path.exists():
        print(f"ERROR: Container not found: {container_path}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0

    with open(container_path, "rb") as f:
        magic = f.read(4)
        if magic != b"PAH1":
            print("ERROR: Not a valid PAH container")
            return False

        version = int.from_bytes(f.read(4), "little")
        entry_count = int.from_bytes(f.read(4), "little")
        print(f"Extracting {entry_count} entries from container...")

        for i in range(entry_count):
            try:
                sig_len = int.from_bytes(f.read(4), "little")
                data_len = int.from_bytes(f.read(4), "little")
                name_len = int.from_bytes(f.read(4), "little")

                if name_len == 0 or name_len > 4096:
                    f.read(sig_len + data_len)
                    skipped += 1
                    continue

                raw_name = f.read(name_len)
                filename = raw_name.split(b"\x00")[0].decode("utf-8", errors="ignore")
                filename = "".join(c for c in filename if c.isprintable() or c in "._- ")
                if not filename or len(filename) < 3:
                    filename = f"entry_{i:04d}"

                f.read(sig_len)
                raw_data = f.read(data_len)
                final_data = unwrap_pah_layers(raw_data)

                try:
                    decoded = final_data.decode("utf-8", errors="ignore")
                    wrapper_b = json.loads(decoded)

                    if isinstance(wrapper_b, dict) and wrapper_b.get("header", {}).get("is_hidden_internal"):
                        print(f"🔒 Hidden manifest found in entry: {filename}")

                        b64_data = wrapper_b.get("data_b64", "")
                        header = wrapper_b.get("header", {})
                        original_name = header.get("original_filename", filename)

                        if wrapper_b.get("payload_encrypted"):
                            pw = password if password else None
                            if not pw:
                                pw = prompt_for_password_with_retries(original_name, max_attempts=3)

                            if pw:
                                kdf_salt_b64 = header.get("kdf_salt_b64")
                                decrypted = try_decrypt_payload(b64_data, pw, kdf_salt_b64)
                                if decrypted:
                                    extracted_data = decrypted
                                    filename = original_name
                                    print(f"✅ Unlocked successfully: {filename}")
                                else:
                                    print(f"❌ All password attempts failed for protected entry: {original_name}")
                                    print("   → Skipping (asset remains protected).")
                                    skipped += 1
                                    continue
                            else:
                                print(f"🔐 No password supplied for protected entry: {original_name}")
                                print("   → Skipping (asset remains protected).")
                                skipped += 1
                                continue
                        else:
                            extracted_data = base64.b64decode(b64_data) if b64_data else final_data
                            filename = original_name
                    else:
                        extracted_data = final_data
                except Exception:
                    extracted_data = final_data

                out_path = output_dir / filename
                out_path.write_bytes(extracted_data)
                print(f"  Extracted: {filename}")
                count += 1

            except Exception as e:
                print(f"  Skipped bad entry {i}: {e}")
                skipped += 1
                continue

    print(f"\n✅ Extracted {count} files | Skipped {skipped} protected/bad entries → {output_dir}")
    return True


def smart_extract(input_path: Path, output_dir: Path, password: Optional[str] = None):
    input_path = input_path.resolve()

    if input_path.is_dir():
        pqc_files = sorted(
            [f for f in input_path.rglob("*") if f.is_file() and f.suffix.lower() == ".pqcasset"]
        )

        if not pqc_files:
            print(f"No .pqcasset files found in: {input_path}")
            return False

        if len(pqc_files) == 1 and is_multi_container(pqc_files[0]):
            print(f"Found container in directory. Extracting contents directly...")
            return extract_from_container(pqc_files[0], output_dir, password=password)

        print(f"Found {len(pqc_files)} .pqcasset file(s) in directory. Extracting...")
        for pqc_file in pqc_files:
            print(f"\n→ Extracting: {pqc_file.name}")
            if is_multi_container(pqc_file):
                extract_from_container(pqc_file, output_dir, password=password)
            else:
                extract_wrapped_file(pqc_file, output_dir, password=password)
        print(f"\n✅ Finished processing directory: {input_path}")
        return True

    elif is_multi_container(input_path):
        return extract_from_container(input_path, output_dir, password=password)
    else:
        return extract_wrapped_file(input_path, output_dir, password=password)


def is_multi_container(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"PAH1":
                return False
            version = int.from_bytes(f.read(4), "little")
            entry_count = int.from_bytes(f.read(4), "little")
            return version == 1 and 0 < entry_count < 100000
    except:
        return False


def verify_wrapped_file(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"PAH1":
                return False
            sig_len = int.from_bytes(f.read(4), "little")
            data_len = int.from_bytes(f.read(4), "little")
            return sig_len > 0 and data_len > 0
    except:
        return False


def list_item(path: Path):
    path = path.resolve()
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        return

    if is_multi_container(path):
        print(f"\n📦 Multi-Asset Container: {path.name}")
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != b"PAH1":
                print("Not a valid PAH container")
                return
            version = int.from_bytes(f.read(4), "little")
            entry_count = int.from_bytes(f.read(4), "little")
            print(f"   Total entries: {entry_count}\n")
            for i in range(entry_count):
                sig_len = int.from_bytes(f.read(4), "little")
                data_len = int.from_bytes(f.read(4), "little")
                name_len = int.from_bytes(f.read(4), "little")
                raw_name = f.read(name_len)
                filename = raw_name.split(b"\x00")[0].decode("utf-8", errors="ignore")
                f.read(sig_len)
                f.read(data_len)
                print(f"   [{i}] {filename} ({data_len} bytes)")
    else:
        print(f"\n📦 Single Wrapped File: {path.name}")
        manifest = path.with_suffix(".pqcasset.manifest.json")
        if manifest.exists():
            m = json.loads(manifest.read_text())
            print(f"   Original: {m.get('original_filename')}")
            print(f"   Algorithm: {m.get('algorithm')}")


def verify_container(container_path: Path, quiet: bool = False) -> bool:
    container_path = container_path.resolve()
    if not container_path.exists():
        print(f"ERROR: File not found: {container_path}")
        return False

    print(f"\n🔍 Verifying: {container_path.name}")

    try:
        with open(container_path, "rb") as f:
            magic = f.read(4)
            if magic != b"PAH1":
                print("❌ Invalid magic bytes (not a PAH container)")
                return False

            version = int.from_bytes(f.read(4), "little")
            entry_count = int.from_bytes(f.read(4), "little")

            print(f"   Type: Multi-Asset Container | Version: {version} | Entries: {entry_count}")

            valid = 0
            invalid = 0

            for i in range(entry_count):
                try:
                    sig_len = int.from_bytes(f.read(4), "little")
                    data_len = int.from_bytes(f.read(4), "little")
                    name_len = int.from_bytes(f.read(4), "little")

                    if sig_len == 0 or data_len == 0 or name_len == 0:
                        invalid += 1
                        f.read(sig_len + data_len + name_len)
                        continue

                    raw_name = f.read(name_len)
                    filename = raw_name.split(b"\x00")[0].decode("utf-8", errors="ignore")

                    f.read(sig_len)
                    f.read(data_len)

                    if filename:
                        valid += 1
                        if not quiet:
                            print(f"   ✅ [{i}] {filename}  (sig: {sig_len}, data: {data_len})")
                    else:
                        invalid += 1

                except Exception:
                    invalid += 1
                    break

            print(f"\n   Result: {valid} valid | {invalid} invalid")

            if invalid == 0:
                print("✅ Container verification passed")
                return True
            else:
                print("⚠️  Container has some invalid entries")
                return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def split_container(container_path: Path, num_parts: int, output_prefix: str, algorithm: str = "hybrid"):
    container_path = container_path.resolve()
    if not container_path.exists():
        print(f"ERROR: Container not found: {container_path}")
        return False

    temp_dir = Path(tempfile.mkdtemp(prefix="pqc_split_"))
    if not smart_extract(container_path, temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    all_files = sorted([f for f in temp_dir.iterdir() if f.is_file()])
    if not all_files:
        print("Container is empty.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    chunk_size = max(1, len(all_files) // num_parts)
    chunks = [all_files[i:i + chunk_size] for i in range(0, len(all_files), chunk_size)]

    created = []
    for idx, chunk in enumerate(chunks, 1):
        part_name = f"{output_prefix}_part{idx}"
        part_container = container_path.parent / f"{part_name}.pqcasset"

        run_pah([find_pah_binary(), "--create-container", str(part_container)])
        for file in chunk:
            run_pah([find_pah_binary(), "--add-to-container", str(part_container), str(file)])

        created.append(part_container)
        print(f"  Created: {part_container.name} ({len(chunk)} files)")

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"\n✅ Split into {len(created)} containers")
    return created


def split_container_by_size(container_path: Path, target_size_str: str, output_prefix: str, algorithm: str = "hybrid"):
    container_path = container_path.resolve()
    if not container_path.exists():
        print(f"ERROR: Container not found: {container_path}")
        return False

    target_size = parse_human_size(target_size_str)
    print(f"Splitting by approximate size: {target_size_str} ({target_size} bytes)")

    temp_dir = Path(tempfile.mkdtemp(prefix="pqc_split_size_"))
    if not smart_extract(container_path, temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    all_files = sorted([f for f in temp_dir.iterdir() if f.is_file()], key=lambda x: x.stat().st_size, reverse=True)

    groups = []
    current_group = []
    current_size = 0

    for f in all_files:
        file_size = f.stat().st_size
        if current_size + file_size > target_size and current_group:
            groups.append(current_group)
            current_group = []
            current_size = 0
        current_group.append(f)
        current_size += file_size

    if current_group:
        groups.append(current_group)

    created = []
    for idx, group in enumerate(groups, 1):
        part_name = f"{output_prefix}_part{idx}"
        part_container = container_path.parent / f"{part_name}.pqcasset"

        run_pah([find_pah_binary(), "--create-container", str(part_container)])
        for file in group:
            run_pah([find_pah_binary(), "--add-to-container", str(part_container), str(file)])

        created.append(part_container)
        total_size = sum(f.stat().st_size for f in group)
        print(f"  Created: {part_container.name} ({len(group)} files, ~{total_size / (1024**2):.1f} MB)")

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"\n✅ Split into {len(created)} containers by size")
    return created


def clean_stacked_files(directory: Path = Path("pqc_wrapped")):
    directory = directory.resolve()
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    cleaned = 0
    for f in list(directory.glob("*")):
        if f.is_file() and f.name.count(".pqcasset") >= 2:
            clean_name = f.name.split(".pqcasset")[0] + ".pqcasset"
            target = f.parent / clean_name
            if target.exists():
                f.unlink()
            else:
                f.rename(target)
            print(f"Cleaned: {f.name}")
            cleaned += 1
    print(f"✅ Cleaned {cleaned} stacked files")


# ==================== MAIN ====================

def main():
    global PAH_BINARY

    parser = argparse.ArgumentParser(
        description="PQC Scout-Knife v2.8.2 - Secure source handling with DRM-style wipe"
    )
    parser.add_argument("input", nargs="*", help="File(s), folder or container")
    parser.add_argument("--algorithm", choices=SUPPORTED_ALGORITHMS, default=DEFAULT_ALGORITHM)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base64", action="store_true")
    parser.add_argument("--hash", action="store_true")
    parser.add_argument("--container", action="store_true")
    parser.add_argument("--name", help="Container name (required with --container)")
    parser.add_argument("--keep-temps", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--extract-all", action="store_true")
    parser.add_argument("--split", type=int, metavar="N")
    parser.add_argument("--output-prefix", help="Prefix for split parts")
    parser.add_argument("--clean-stacked", action="store_true")
    parser.add_argument("--split-size", help="Split by approximate size")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--public-manifest", action="store_true")
    parser.add_argument("--password", type=str, default=None)
    parser.add_argument("--keep-source", action="store_true",
                        help="Keep original source files/folders (COPY only, disables move/shred/archive-cleanup)")
    parser.add_argument("--keep-archives", action="store_true",
                        help="Do NOT securely wipe+delete the source_archives/ after container creation (default: cleanup to avoid lingering husks)")
    parser.add_argument("--no-nested", action="store_true")
    parser.add_argument("--pah-binary", type=str, default=None)
    parser.add_argument("--version", action="version", version="PQC Scout-Knife v2.9.0-phase1-secure-shred-kdf-seeds")

    args = parser.parse_args()

    if args.pah_binary:
        PAH_BINARY = args.pah_binary

    PAH_BINARY = find_pah_binary()
    resolved_pw = resolve_password(args.password)
    if resolved_pw:
        check_crypto_for_password()

    if args.clean_stacked:
        clean_stacked_files()
        return

    if args.list:
        if args.input:
            list_item(Path(args.input[0]))
        return

    if args.extract or args.extract_all:
        if args.input:
            smart_extract(Path(args.input[0]), args.output_dir, password=resolved_pw)
        return

    if args.split_size:
        if args.input:
            prefix = args.output_prefix or Path(args.input[0]).stem
            split_container_by_size(Path(args.input[0]), args.split_size, prefix, args.algorithm)
        return

    if args.split:
        if args.input:
            prefix = args.output_prefix or Path(args.input[0]).stem
            split_container(Path(args.input[0]), args.split, prefix, args.algorithm)
        return

    if args.verify:
        if args.input:
            input_path = Path(args.input[0]).resolve()
            if is_multi_container(input_path):
                verify_container(input_path, quiet=args.quiet)
            else:
                if verify_wrapped_file(input_path):
                    print(f"✅ Structurally valid: {input_path.name}")
                else:
                    print(f"❌ Verification failed: {input_path.name}")
        return

    if not args.input:
        parser.print_help()
        return

    if len(args.input) > 1 and not args.container:
        print(f"Wrapping {len(args.input)} files individually...")
        embed = not args.no_nested
        pub = args.public_manifest

        for file_arg in args.input:
            p = Path(file_arg).resolve()
            if p.is_file():
                wrap_single_file(p, args.output_dir, args.algorithm,
                                 use_base64=args.base64, add_hash=args.hash,
                                 quiet=args.quiet, embed_manifest=embed,
                                 public_manifest=pub, password=resolved_pw, nested=embed)
            else:
                print(f"Skipping (not a file): {file_arg}")
        return

    input_path = Path(args.input[0]).resolve()

    if args.container:
        if not args.name:
            print("ERROR: --name is required with --container")
            return
        wrap_folder_as_container(input_path, args.output_dir, args.name, args.algorithm,
                                 keep_temps=args.keep_temps, quiet=args.quiet,
                                 password=resolved_pw,
                                 keep_source=args.keep_source,
                                 cleanup_archives=not args.keep_archives)
    else:
        embed = not args.no_nested
        pub = args.public_manifest

        if input_path.is_file():
            wrap_single_file(input_path, args.output_dir, args.algorithm,
                             use_base64=args.base64, add_hash=args.hash, quiet=args.quiet,
                             embed_manifest=embed, public_manifest=pub, password=resolved_pw, nested=embed)
        elif input_path.is_dir():
            for f in input_path.rglob("*"):
                if f.is_file():
                    wrap_single_file(f, args.output_dir, args.algorithm,
                                     use_base64=args.base64, add_hash=args.hash, quiet=args.quiet,
                                     embed_manifest=embed, public_manifest=pub, password=resolved_pw, nested=embed)
        else:
            print(f"ERROR: {input_path} is not a file or directory")


if __name__ == "__main__":
    main()
