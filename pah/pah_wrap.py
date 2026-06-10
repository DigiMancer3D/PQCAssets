#!/usr/bin/env python3
"""
pah_wrap_improved.py v2.7 - Reliable clean container filenames
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
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

DEFAULT_OUTPUT_DIR = Path("pqc_wrapped")
DEFAULT_ALGORITHM = "falcon"
SUPPORTED_ALGORITHMS = ["falcon", "sphincs", "hybrid"]

PAH_BINARY = None

def parse_human_size(size_str: str) -> int:
    """Convert human-readable size (e.g. 100M, 500MB, 2G) to bytes."""
    size_str = size_str.strip().upper().replace(" ", "")
    multipliers = {
        'K': 1024,
        'KB': 1024,
        'M': 1024**2,
        'MB': 1024**2,
        'G': 1024**3,
        'GB': 1024**3,
        'T': 1024**4,
        'TB': 1024**4,
    }
    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            try:
                num = float(size_str[:-len(suffix)])
                return int(num * mult)
            except ValueError:
                pass
    # Assume bytes if no suffix
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")

def find_pah_binary() -> str:
    global PAH_BINARY
    if PAH_BINARY:
        return PAH_BINARY
    candidates = [
        Path.cwd() / "pah" / "pah",
        Path.home() / "PQCassets" / "pah" / "pah",
        Path("/home/z0m8i3d/PQCassets/pah/pah"),
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            PAH_BINARY = str(c.resolve())
            return PAH_BINARY
    print("ERROR: pah binary not found")
    sys.exit(1)


def run_pah(cmd: List[str], timeout: int = 120, cwd: str = None) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as e:
        return False, str(e)


def compute_content_hash(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


# ==================== WRAPPING ====================

def wrap_single_file(input_path: Path, output_dir: Path, algorithm: str,
                     use_base64=False, add_hash=False, quiet=False) -> Optional[Path]:
    input_path = input_path.resolve()
    if not input_path.exists() or not input_path.is_file():
        if not quiet:
            print(f"ERROR: File not found: {input_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    original_data = input_path.read_bytes()
    final_data = original_data

    manifest = {
        "original_filename": input_path.name,
        "original_size": len(original_data),
        "wrapped_at": datetime.now(timezone.utc).isoformat() + "Z",
        "algorithm": algorithm,
        "base64_encoded": use_base64,
        "content_hash": None,
        "pah_wrapper_version": "2.7",
    }

    if use_base64:
        final_data = base64.b64encode(original_data)

    if add_hash:
        content_hash = compute_content_hash(original_data)
        manifest["content_hash"] = content_hash
        hash_suffix = content_hash[:12]
        base_name = f"{input_path.stem}_{hash_suffix}{input_path.suffix}"
    else:
        base_name = input_path.name

    temp_path = None
    if use_base64 or add_hash:
        temp_path = output_dir / f".tmp_{input_path.name}"
        temp_path.write_bytes(final_data)
        input_path = temp_path

    output_path = output_dir / f"{base_name}.pqcasset"
    success, _ = run_pah([find_pah_binary(), f"--wrap-{algorithm}", str(input_path), str(output_path)])

    if temp_path and temp_path.exists():
        temp_path.unlink()

    if success:
        manifest_path = output_path.with_suffix(".pqcasset.manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2))
        if not quiet:
            print(f"✅ Wrapped ({algorithm}): {output_path.name}")
        return output_path
    return None


def wrap_folder_as_container(folder: Path, output_dir: Path, name: str, algorithm: str,
                             keep_temps: bool = False, quiet: bool = False) -> Optional[Path]:
    folder = folder.resolve()
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    container_path = output_dir / f"{name}.pqcasset"
    temp_dir = Path(tempfile.mkdtemp(prefix="pqc_prewrap_"))

    if not quiet:
        print(f"Creating PQC container '{name}' using algorithm={algorithm}")

    prewrapped: List[Path] = []
    files = [f for f in folder.rglob("*") if f.is_file()]
    total = len(files)

    for i, f in enumerate(files, 1):
        if not quiet:
            print(f"  [{i}/{total}] Pre-wrapping {f.name} ...", end=" ")

        wrapped = wrap_single_file(f, temp_dir, algorithm, use_base64=False, add_hash=True, quiet=True)

        if wrapped:
            clean_name = wrapped.name
            clean_path = temp_dir / clean_name

            if wrapped != clean_path:
                if clean_path.exists():
                    clean_path.unlink()
                shutil.move(str(wrapped), str(clean_path))

            prewrapped.append(clean_path)
            if not quiet:
                print("✓")
        else:
            if not quiet:
                print("✗")

    if not prewrapped:
        print("No files successfully pre-wrapped. Aborting.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    success, _ = run_pah([find_pah_binary(), "--create-container", str(container_path)])
    if not success:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    # === RELIABLE CLEAN BASENAME METHOD ===
    # Copy clean files temporarily to current directory, add them, then delete copies
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
        else:
            if not quiet:
                print(f"  ! Failed to add {copy_path.name}")

    # Cleanup temporary copies
    for p in temp_copies:
        if p.exists():
            p.unlink()

    if not keep_temps:
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print(f"Pre-wrapped files kept in: {temp_dir}")

    if not quiet:
        print(f"\n✅ PQC Zip Container created: {container_path}")
        print(f"   Entries: {added} | Inner: {algorithm} | Outer per-entry: Falcon")

    return container_path


# ==================== DETECTION, LIST, EXTRACT, SPLIT, CLEAN ====================

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

                    f.read(sig_len)  # skip signature
                    f.read(data_len)  # skip data

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

def extract_wrapped_file(wrapped_path: Path, output_dir: Path):
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
        data = f.read(data_len)

    manifest = wrapped_path.with_suffix(".pqcasset.manifest.json")
    original_name = wrapped_path.stem
    if manifest.exists():
        try:
            m = json.loads(manifest.read_text())
            original_name = m.get("original_filename", original_name)
        except:
            pass

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / original_name).write_bytes(data)
    print(f"✅ Extracted + Verified: {original_name} → {output_dir}")
    return True


def extract_from_container(container_path: Path, output_dir: Path):
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
                    # Skip obviously bad entries
                    f.read(sig_len + data_len)
                    skipped += 1
                    continue

                raw_name = f.read(name_len)
                filename = raw_name.split(b"\x00")[0].decode("utf-8", errors="ignore")
                filename = "".join(c for c in filename if c.isprintable() or c in "._- ")

                # Fallback to safe name if parsing fails badly
                if not filename or len(filename) < 3:
                    filename = f"entry_{i:04d}"

                f.read(sig_len)  # skip signature
                data = f.read(data_len)

                out_path = output_dir / filename
                out_path.write_bytes(data)
                print(f"  Extracted: {filename}")
                count += 1

            except Exception as e:
                print(f"  Skipped bad entry {i}: {e}")
                skipped += 1
                continue

    print(f"\n✅ Extracted {count} files | Skipped {skipped} bad entries → {output_dir}")
    return True


def smart_extract(input_path: Path, output_dir: Path):
    if is_multi_container(input_path):
        return extract_from_container(input_path, output_dir)
    else:
        return extract_wrapped_file(input_path, output_dir)


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
    PAH_BINARY = find_pah_binary()

    parser = argparse.ArgumentParser(description="PAH Bulk PQC Wrapper v2.7")
    parser.add_argument("input", nargs="?", help="File, folder or container")
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
    parser.add_argument("--split", type=int, metavar="N", help="Split into N parts")
    parser.add_argument("--output-prefix", help="Prefix for split parts")
    parser.add_argument("--clean-stacked", action="store_true")

    parser.add_argument("--split-size", help="Split by approximate size (e.g. 100M, 500MB, 2G)")
    parser.add_argument("--verify", action="store_true", help="Verify container or file integrity")

    args = parser.parse_args()

    if args.clean_stacked:
        clean_stacked_files()
        return

    if args.list:
        if args.input:
            list_item(Path(args.input))
        return

    if args.extract or args.extract_all:
        if args.input:
            smart_extract(Path(args.input), args.output_dir)
        return

    if args.split_size:
        if args.input:
            prefix = args.output_prefix or Path(args.input).stem
            split_container_by_size(Path(args.input), args.split_size, prefix, args.algorithm)
        return

    if args.split:
        if args.input:
            prefix = args.output_prefix or Path(args.input).stem
            split_container(Path(args.input), args.split, prefix, args.algorithm)
        return

    if args.verify:
        if args.input:
            input_path = Path(args.input).resolve()
            if is_multi_container(input_path):
                verify_container(input_path, quiet=args.quiet)
            else:
                if verify_wrapped_file(input_path):
                    print(f"✅ Single wrapped file is structurally valid: {input_path.name}")
                else:
                    print(f"❌ Single wrapped file failed verification: {input_path.name}")
        return

    if not args.input:
        parser.print_help()
        return

    input_path = Path(args.input).resolve()

    if args.container:
        if not args.name:
            print("ERROR: --name is required with --container")
            return
        wrap_folder_as_container(input_path, args.output_dir, args.name, args.algorithm,
                                 keep_temps=args.keep_temps, quiet=args.quiet)
    else:
        if input_path.is_file():
            wrap_single_file(input_path, args.output_dir, args.algorithm,
                             use_base64=args.base64, add_hash=args.hash, quiet=args.quiet)
        elif input_path.is_dir():
            for f in input_path.rglob("*"):
                if f.is_file():
                    wrap_single_file(f, args.output_dir, args.algorithm,
                                     use_base64=args.base64, add_hash=args.hash, quiet=args.quiet)
        else:
            print(f"ERROR: {input_path} is not a file or directory")


if __name__ == "__main__":
    main()
