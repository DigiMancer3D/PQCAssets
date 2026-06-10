#!/usr/bin/env python3
"""
run_phase5_tests.py
Correct runner for Phase 5 tests located in economy/tests/

Place this file in ~/PQCassets/

Usage:
    cd ~/PQCassets
    python3 run_phase5_tests.py
"""

import os
import importlib.util

def run_test_from_tests_folder(filename):
    """Load and run a test file from economy/tests/"""
    filepath = os.path.join("economy", "tests", filename)
    
    if not os.path.exists(filepath):
        print(f"✗ File not found: {filepath}")
        return False

    print(f"\n{'='*60}")
    print(f"Running: {filename}")
    print('='*60)

    try:
        spec = importlib.util.spec_from_file_location("test_module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "main"):
            module.main()
            print(f"✓ {filename} completed successfully")
            return True
        else:
            print(f"⚠ {filename} has no main() function")
            return False
    except Exception as e:
        print(f"✗ {filename} failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("Running Phase 5 Economy Tests...")

    test_files = [
        "test_phase5_full_flow.py",
        "test_bsim_bridge.py",
        "test_end_to_end_pipeline.py",
    ]

    success_count = 0
    for test_file in test_files:
        if run_test_from_tests_folder(test_file):
            success_count += 1

    print("\n" + "="*60)
    print(f"Completed {success_count}/{len(test_files)} tests successfully.")
    print("="*60)


if __name__ == "__main__":
    main()
