#!/usr/bin/env python3
"""
New_Thing Phase 0: Auto-Installer & Bootstrap
=============================================

One-command setup for the entire hybrid PQC + SVC + FusionHash project.

What it does (idempotent & smart):
1. Creates a project-level virtual environment at .venv/ (reused on future runs)
2. Installs all Python dependencies from requirements.txt (only once or when missing)
3. Detects Rust toolchain; if missing, gives clear one-line install command
4. Builds the Rust Bulletproofs extension (rust_bulletproofs) via maturin (the part that was hard before)
5. Makes existing auto-checks in fusion_hash.py etc. always succeed
6. Creates .setup_complete marker so re-runs are fast (shallow checks only)
7. Prints final activation command + quick test

After running this once, you can do:
    source .venv/bin/activate
    python3 -m keygen.unified_sphinx_keygen
    python3 wallet/btc_checker.py
    python3 fusion/fusion_hash.py
    etc.

All dependency pulls happen only on first run (or if you delete .venv).
Subsequent runs do fast import + version checks.

Run this from the PQCassets/ root:
    python3 setup.py
"""

import os
import sys
import subprocess
import shutil
import venv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_DIR = PROJECT_ROOT / ".venv"
SETUP_MARKER = PROJECT_ROOT / ".setup_complete"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

# Colors for nice output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_step(msg):
    print(f"{BOLD}{GREEN}▶ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def run(cmd, cwd=None, check=True, capture=False):
    """Run shell command with nice output."""
    print(f"   $ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        if capture:
            return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
        else:
            return subprocess.run(cmd, cwd=cwd, check=check)
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        raise

def get_venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"

def get_venv_pip():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "pip"
    return VENV_DIR / "bin" / "pip"

def create_or_update_venv():
    if not VENV_DIR.exists():
        print_step("Creating project virtual environment (.venv)")
        try:
            # Compatible with Python 3.8+ (removed upgrade_seed for older versions)
            venv.create(VENV_DIR, with_pip=True)
            print(f"{GREEN}   ✓ Created {VENV_DIR}{RESET}")
        except Exception as e:
            print_error(f"Failed to create virtual environment: {e}")
            print("Trying alternative method using subprocess...")
            try:
                subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
                print(f"{GREEN}   ✓ Created {VENV_DIR} via subprocess{RESET}")
            except Exception as e2:
                print_error(f"Both methods failed: {e2}")
                raise
    else:
        print(f"{GREEN}   ✓ Reusing existing virtual environment{RESET}")

def install_requirements():
    pip = get_venv_pip()
    py = get_venv_python()

    print_step("Upgrading pip, setuptools, wheel in venv")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)

    if REQUIREMENTS.exists():
        print_step("Installing project requirements (coincurve, cryptography, requests, base58, ...)")
        run([str(pip), "install", "-r", str(REQUIREMENTS)], check=True)
    else:
        print_warning("requirements.txt not found — skipping")

def ensure_rust_toolchain():
    """Check for rustc + cargo. Give friendly instructions if missing."""
    rustc = shutil.which("rustc")
    cargo = shutil.which("cargo")
    if rustc and cargo:
        print(f"{GREEN}   ✓ Rust toolchain found: {rustc}{RESET}")
        return True
    else:
        print_warning("Rust toolchain not found (needed for Bulletproofs / maturin build)")
        print(f"""
{BOLD}Please install Rust with one command:{RESET}
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

Then re-run this setup:
    python3 setup.py
""")
        return False

def build_rust_extension():
    """Build rust_bulletproofs via maturin (the previously hard step)."""
    py = get_venv_python()
    pip = get_venv_pip()
    fusion_dir = PROJECT_ROOT / "fusion"

    if not (fusion_dir / "Cargo.toml").exists():
        print_warning("fusion/Cargo.toml not found — skipping Rust Bulletproofs build")
        return False

    print_step("Installing maturin (build tool for Rust Python extensions)")
    run([str(pip), "install", "maturin>=1.5,<2.0"], check=True)

    print_step("Building rust_bulletproofs extension (this may take 1-3 minutes first time)")
    try:
        # maturin develop installs directly into the active venv
        result = run([
            str(py), "-m", "maturin", "develop", "--release"
        ], cwd=fusion_dir, check=False, capture=True)

        if result.returncode != 0:
            print_error("maturin build failed. Output:")
            print(result.stdout)
            print(result.stderr)
            return False

        print(f"{GREEN}   ✓ rust_bulletproofs compiled and installed into .venv{RESET}")
        return True
    except Exception as e:
        print_error(f"Failed to build Rust extension: {e}")
        return False

def test_critical_imports():
    """Verify that the auto-checks in the project will now pass."""
    py = get_venv_python()
    print_step("Verifying critical imports (so existing auto-checks always succeed)")

    tests = [
        ("coincurve", "from coincurve import PrivateKey, PublicKey"),
        ("cryptography (Fernet)", "from cryptography.fernet import Fernet"),
        ("requests", "import requests"),
        ("base58 (or internal fallback)", "import base58"),
    ]

    all_good = True
    for name, code in tests:
        try:
            run([str(py), "-c", code], capture=True, check=True)
            print(f"   ✓ {name}")
        except:
            print_warning(f"   Could not import {name} (some features may be limited)")
            all_good = False

    # Special test for the Rust extension (important for performance)
    rust_ok = False
    try:
        run([str(py), "-c", "import rust_bulletproofs; print('rust_bulletproofs OK')"], capture=True, check=True)
        print(f"   ✓ rust_bulletproofs (Bulletproofs range proofs)")
        rust_ok = True
    except:
        print_warning("   rust_bulletproofs not available (FusionHash will use Python fallback)")

    # If Rust extension is missing, we want to trigger a rebuild attempt
    if not rust_ok:
        all_good = False

    return all_good

def create_marker():
    marker_data = {
        "setup_time": subprocess.check_output(["date"]).decode().strip(),
        "python": str(get_venv_python()),
        "venv": str(VENV_DIR),
        "version": "Phase 0 - New_Thing Bootstrap v1.0"
    }
    SETUP_MARKER.write_text(json.dumps(marker_data, indent=2))
    print(f"{GREEN}   ✓ Created setup marker {SETUP_MARKER.name}{RESET}")

def main():
    print(f"\n{BOLD}{GREEN}╔════════════════════════════════════════════════════════════╗")
    print(f"║   New_Thing Phase 0 Auto-Installer & Bootstrap             ║")
    print(f"║   Hybrid PQC Wallet + SVC Economy - One-time Setup         ║")
    print(f"╚════════════════════════════════════════════════════════════╝{RESET}\n")

    # Basic Python version guard (project targets 3.8+)
    if sys.version_info < (3, 8):
        print_error("Python 3.8 or newer is required.")
        print("Please upgrade Python and try again.")
        sys.exit(1)
    print(f"   Python {sys.version.split()[0]} detected — good.")

    if SETUP_MARKER.exists():
        print(f"{GREEN}Setup marker found — performing fast verification only...{RESET}")
        if test_critical_imports():
            print(f"\n{GREEN}Everything looks good! No changes needed.{RESET}")
            print_final_instructions()
            return
        else:
            print_warning("Some imports failed — will re-install missing pieces...")

    create_or_update_venv()
    install_requirements()

    rust_ok = ensure_rust_toolchain()
    if rust_ok:
        build_rust_extension()
    else:
        print_warning("Skipping Rust Bulletproofs build (you can re-run setup.py after installing Rust)")

    test_critical_imports()
    create_marker()

    print(f"\n{BOLD}{GREEN}╔════════════════════════════════════════════════════════════╗")
    print(f"║                    SETUP COMPLETE!                         ║")
    print(f"╚════════════════════════════════════════════════════════════╝{RESET}")
    print_final_instructions()

def print_final_instructions():
    activate_cmd = "source .venv/bin/activate" if os.name != "nt" else ".venv\\Scripts\\activate"
    print(f"""
{BOLD}To use New_Thing from now on:{RESET}

    {activate_cmd}
    python3 -m keygen.unified_sphinx_keygen
    python3 PQCassets.py
    python3 wallet/btc_checker.py          # GUI
    python3 fusion/fusion_hash.py
    python3 utils/chain_fusion_tool.py --help

{GREEN}All dependencies are now permanently installed in .venv and will be reused.{RESET}
Re-run {BOLD}python3 setup.py{RESET} anytime to verify or repair.

{BOLD}Next (Phase 1+):{RESET}
- Copy your full sphincs-btc-pipeline/ and sphincs_bch_hybrid/ folders into PQCassets/pqc/
- Start building real keys, mint SVC coins, run the checker GUI, etc.

Enjoy the hybrid PQC + confidential SVC system! 🚀
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
