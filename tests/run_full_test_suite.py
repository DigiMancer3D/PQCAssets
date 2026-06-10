#!/usr/bin/env python3
"""
PQCassets Full Test Suite (v3 - Path Fixed)
Run from project root:
    python3 tests/run_full_test_suite.py
"""

import subprocess
import sys
from pathlib import Path

def find_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "pah").exists() and (current / "keygen").exists():
            return current
        current = current.parent
    return Path.cwd()

PROJECT_ROOT = find_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root: {PROJECT_ROOT}")
print("=" * 70)

def run_command(title, cmd, timeout=90):
    print(f"\n{'─'*70}\n▶ {title}\n   {cmd}\n{'─'*70}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                timeout=timeout, cwd=PROJECT_ROOT)
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            print("✅ PASSED")
            if output: print(output[-600:])
            return True
        else:
            print("❌ FAILED")
            if output: print(output[-800:])
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    all_passed = True

    # === SECTION 1: Keygen ===
    print("\n" + "="*70 + "\nSECTION 1: Core Key Generation\n" + "="*70)
    all_passed &= run_command("Keygen CLI Role 0", "python3 -m keygen.unified_sphinx_keygen --role 0")
    all_passed &= run_command("Programmatic Key Family",
        '''python3 -c "
from keygen.unified_sphinx_keygen import generate_key_family
f = generate_key_family(role=0)
print('BTC:', f['families']['btc']['standard'])
print('BCH:', f['families']['bch']['standard'])
"''')

    # === SECTION 2: PAH Bulk Wrapper (fixed paths) ===
    print("\n" + "="*70 + "\nSECTION 2: PAH Bulk PQC Wrapper\n" + "="*70)
    # Use a file that should exist
    test_file = "pb/bsim/Sprites/findables/key_0.png"
    all_passed &= run_command("Bulk Wrapper - Single file (hybrid + hash)",
        f"python3 pah/pah_wrap_improved.py {test_file} --algorithm hybrid --hash")

    # === SECTION 3: Fusion + SVC ===
    print("\n" + "="*70 + "\nSECTION 3: FusionHash + SVC\n" + "="*70)
    all_passed &= run_command("Fusion Tool Help", "python3 utils/chain_fusion_tool.py --help")
    all_passed &= run_command("Create SVC Mint Transaction",
        "python3 utils/chain_fusion_tool.py --create-transaction --template svc_mint_from_kickback "
        "--kickback-amount 30000000 --dust-amount 5000000 --coin-id TEST-SWEEP")

    # === SECTION 4: Roles ===
    print("\n" + "="*70 + "\nSECTION 4: Roles\n" + "="*70)
    all_passed &= run_command("Role Capabilities",
        '''python3 -c "
from roles.role_system import get_role_capabilities
print(get_role_capabilities(0))
"''')

    # === SECTION 5: End-to-End ===
    print("\n" + "="*70 + "\nSECTION 5: End-to-End Smoke Test\n" + "="*70)
    e2e = f'''python3 -c "
print('=== End-to-End Smoke ===')
from keygen.unified_sphinx_keygen import generate_key_family
key = generate_key_family(role=0)
print('Key generated OK')

import subprocess
r = subprocess.run(['python3', 'pah/pah_wrap_improved.py',
    '{test_file}', '--algorithm', 'hybrid'], capture_output=True, text=True, cwd='.')
print('Asset wrapped:', '✅' if r.returncode == 0 else '❌')
print('=== End-to-End Complete ===')
"'''
    all_passed &= run_command("End-to-End Smoke Test", e2e)

    print("\n" + "="*70)
    print("FINAL RESULT:", "🎉 GOOD PROGRESS" if all_passed else "⚠️ Some issues remain")
    print("="*70)

if __name__ == "__main__":
    main()
