#!/usr/bin/env python3
"""
PQCassets Full Test Suite (v4.1 - PAH Wrapper + Size Split + Timing)
Run from project root:
    python3 tests/run_full_test_suite.py
"""

import subprocess
import sys
import time
from pathlib import Path

def find_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(8):
        if (current / "pah").exists() and (current / "keygen").exists():
            return current
        current = current.parent
    return Path.cwd()

PROJECT_ROOT = find_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root: {PROJECT_ROOT}")
print("=" * 70)

def run_command(title, cmd, timeout=120):
    print(f"\n{'─'*70}\n▶ {title}\n   {cmd}\n{'─'*70}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=PROJECT_ROOT
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            print("✅ PASSED")
            if output:
                print(output[-650:])
            return True
        else:
            print("❌ FAILED")
            if output:
                print(output[-850:])
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    all_passed = True

    # =====================================================
    # SECTION 1: Core Key Generation
    # =====================================================
    print("\n" + "="*70 + "\nSECTION 1: Core Key Generation\n" + "="*70)
    all_passed &= run_command("Keygen CLI - Role 0", "python3 -m keygen.unified_sphinx_keygen --role 0")
    all_passed &= run_command("Programmatic Key Family",
        '''python3 -c "
from keygen.unified_sphinx_keygen import generate_key_family
f = generate_key_family(role=0)
print('BTC:', f['families']['btc']['standard'])
print('BCH:', f['families']['bch']['standard'])
"''')

    # =====================================================
    # SECTION 2: PAH Bulk PQC Wrapper - Full Lifecycle
    # =====================================================
    print("\n" + "="*70 + "\nSECTION 2: PAH Bulk PQC Wrapper - Full Lifecycle\n" + "="*70)

    # Cleanup
    run_command("Cleanup previous test files", "rm -f pqc_wrapped/my_pqc_bundle.pqcasset pqc_wrapped/part_*.pqcasset pqc_wrapped/chunk_*.pqcasset")

    # --- Container Creation & Wrapping ---
    all_passed &= run_command(
        "Create Multi-Asset Container",
        "python3 pah/pah_wrap_improved.py pb/bsim/Sprites/NPCs/ --container --name my_pqc_bundle --algorithm hybrid"
    )

    all_passed &= run_command(
        "Wrap folder individually (findables/)",
        "python3 pah/pah_wrap_improved.py pb/bsim/Sprites/findables/ --algorithm sphincs --hash"
    )

    all_passed &= run_command(
        "Wrap single file with hash + base64",
        "python3 pah/pah_wrap_improved.py pb/bsim/Sprites/Characters/Faux-1PV-shadowed_R.png --algorithm hybrid --base64 --hash"
    )

    # --- Listing ---
    all_passed &= run_command(
        "List container contents",
        "python3 pah/pah_wrap_improved.py pqc_wrapped/my_pqc_bundle.pqcasset --list"
    )

    # --- Extraction ---
    all_passed &= run_command(
        "Extract container",
        "python3 pah/pah_wrap_improved.py pqc_wrapped/my_pqc_bundle.pqcasset --extract-all --output-dir ./restored/"
    )

    # --- Count-based Split ---
    all_passed &= run_command(
        "Split container into 4 parts (by count)",
        "python3 pah/pah_wrap_improved.py pqc_wrapped/my_pqc_bundle.pqcasset --split 4 --output-prefix part"
    )

    # --- Size-based Split (NEW) ---
    all_passed &= run_command(
        "Split container by size (5MB target)",
        "python3 pah/pah_wrap_improved.py pqc_wrapped/my_pqc_bundle.pqcasset --split-size 5M --output-prefix chunk"
    )

    # --- Verification ---
    all_passed &= run_command(
        "Verify container",
        "python3 pah/pah_wrap_improved.py pqc_wrapped/my_pqc_bundle.pqcasset --verify"
    )

    all_passed &= run_command(
        "Extract with verification",
        "python3 pah/pah_wrap_improved.py pqc_wrapped/my_pqc_bundle.pqcasset --extract-all --verify --output-dir ./verified/"
    )

    # --- Repack Demo ---
    all_passed &= run_command(
        "Repack extracted files into new container",
        "python3 pah/pah_wrap_improved.py restored/ --container --name repacked_test --algorithm hybrid"
    )

    # --- Cleanup ---
    all_passed &= run_command(
        "Clean stacked .pqcasset files",
        "python3 pah/pah_wrap_improved.py --clean-stacked"
    )

    # =====================================================
    # SECTION 2.5: PAH Split Performance / Timing
    # =====================================================
    print("\n" + "="*70 + "\nSECTION 2.5: PAH Split Performance Comparison\n" + "="*70)

    # Recreate a clean container for timing tests
    run_command("Recreate clean container for timing",
                "rm -f pqc_wrapped/timing_test.pqcasset && python3 pah/pah_wrap_improved.py pb/bsim/Sprites/NPCs/ --container --name timing_test --algorithm hybrid --quiet")

    # Time count-based split
    start = time.time()
    run_command("Time: Split by count (4 parts)",
                "python3 pah/pah_wrap_improved.py pqc_wrapped/timing_test.pqcasset --split 4 --output-prefix time_count --quiet")
    count_time = time.time() - start
    print(f"⏱️  Count-based split (4 parts) took: {count_time:.2f} seconds")

    # Time size-based split
    start = time.time()
    run_command("Time: Split by size (5MB)",
                "python3 pah/pah_wrap_improved.py pqc_wrapped/timing_test.pqcasset --split-size 5M --output-prefix time_size --quiet")
    size_time = time.time() - start
    print(f"⏱️  Size-based split (~5MB) took:   {size_time:.2f} seconds")

    print(f"\n📊 Performance Summary:")
    print(f"   Count-based split: {count_time:.2f}s")
    print(f"   Size-based split : {size_time:.2f}s")

    # Final cleanup
    run_command("Final cleanup", "rm -f pqc_wrapped/timing_test.pqcasset pqc_wrapped/time_*.pqcasset")

    # =====================================================
    # SECTION 3: Fusion + SVC
    # =====================================================
    print("\n" + "="*70 + "\nSECTION 3: FusionHash + SVC\n" + "="*70)
    all_passed &= run_command("Fusion Tool Help", "python3 utils/chain_fusion_tool.py --help")

    # =====================================================
    # SECTION 4: Roles
    # =====================================================
    print("\n" + "="*70 + "\nSECTION 4: Roles\n" + "="*70)
    all_passed &= run_command("Role Capabilities (Master)",
        '''python3 -c "
from roles.role_system import get_role_capabilities
print(get_role_capabilities(0))
"''')

    # =====================================================
    # SECTION 5: End-to-End Smoke
    # =====================================================
    print("\n" + "="*70 + "\nSECTION 5: End-to-End Smoke Test\n" + "="*70)
    e2e = '''python3 -c "
print('=== End-to-End Smoke ===')
from keygen.unified_sphinx_keygen import generate_key_family
key = generate_key_family(role=0)
print('Key generated OK')

import subprocess
r = subprocess.run(['python3', 'pah/pah_wrap_improved.py',
    'pb/bsim/Sprites/findables/key_0.png', '--algorithm', 'hybrid'],
    capture_output=True, text=True, cwd='.')
print('Asset wrapped:', '✅' if r.returncode == 0 else '❌')
print('=== End-to-End Complete ===')
"'''
    all_passed &= run_command("End-to-End Smoke Test", e2e)

    # =====================================================
    # FINAL RESULT
    # =====================================================
    print("\n" + "="*70)
    print("FINAL RESULT:", "🎉 ALL TESTS PASSED" if all_passed else "⚠️ Some issues remain")
    print("="*70)


if __name__ == "__main__":
    main()
