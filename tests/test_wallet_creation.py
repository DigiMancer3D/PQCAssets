#!/usr/bin/env python3
"""
tests/test_wallet_creation.py
Basic tests for Phase 2 Wallet functionality
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from wallet.wallet import Wallet
from seeds.solar_smt32 import generate_solar_trinary_seed


def test_auto_wallet_creation():
    wallet = Wallet()
    info = wallet.create(seed_method="auto")
    assert "wallet_id" in info
    assert info["role"] in range(10)
    print("✅ Auto wallet creation works")


def test_solar_smt32_seed():
    sample_data = {
        "h": 123456,
        "d": 8730,
        "x": 312,
        "y": 87,
        "z": 42,
        "i": 67,
        "e": 1740000000,
        "checksum": ""
    }
    seed = generate_solar_trinary_seed(sample_data)
    assert len(seed) == 32
    print("✅ Solar SMT32 seed generation works")


if __name__ == "__main__":
    test_auto_wallet_creation()
    test_solar_smt32_seed()
    print("\nAll wallet creation tests passed.")