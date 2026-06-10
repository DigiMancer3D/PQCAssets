#!/usr/bin/env python3
"""
new_thing.py
Phase 3 Demo - Unified Sphinx+ KeyGen + Wallet + Roles + User Secret
"""

from wallet.wallet import Wallet
from roles.role_system import get_role_capabilities, get_master_view_key
from seeds.solar_smt32 import process_solar_smt32_data


def main():
    print("🌌 New_Thing - Phase 3 Demo\n")

    # === 1. Auto seed + default role ===
    print("[1] Creating wallet with auto seed...")
    w1 = Wallet()
    info1 = w1.create(seed_method="auto")
    print(f"   Wallet : {info1['wallet_id']}")
    print(f"   Role   : {info1['role']} ({info1['role_name']})")
    print(f"   BTC    : {info1['btc_address']}")
    w1.save(compatible=True)
    print("   Saved to wallets/ (compatible format)\n")

    # === 2. User Secret seed ===
    print("[2] Creating wallet with user-provided secret...")
    w2 = Wallet()
    info2 = w2.create(seed_method="user_secret", seed_data="MySuperSecretPassword123!")
    print(f"   Wallet : {info2['wallet_id']}")
    print(f"   Role   : {info2['role']}")
    print(f"   BTC    : {info2['btc_address']}")
    w2.save(compatible=True)
    print("   Saved using SHA3-512 + SHAKE (user_secret method)\n")

    # === 3. Solar SMT32 seed + specific role ===
    print("[3] Creating wallet with Solar SMT32 data + Role 0...")
    sample_smt32 = {
        "h": 123456, "d": 8730, "x": 312, "y": 87,
        "z": 42, "i": 67, "e": 1740000000, "checksum": ""
    }
    w3 = Wallet()
    info3 = w3.create(seed_method="solar_smt32", seed_data=sample_smt32, requested_role=0)
    print(f"   Wallet : {info3['wallet_id']}")
    print(f"   Role   : {info3['role']} ({info3['role_name']})")
    w3.save(compatible=True)
    print("   Saved with Master/Admin role\n")

    # === 4. Role Capabilities + Master View Key ===
    print("[4] Role & Master View Key Demo")
    print("   Role 0 Capabilities:", get_role_capabilities(0))
    sample_105 = "a" * 210
    print("   Master View Key (example):", get_master_view_key(sample_105))
    print()

    print("✅ Phase 3 Demo Complete. All systems integrated.")


if __name__ == "__main__":
    main()
