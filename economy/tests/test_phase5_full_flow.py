#!/usr/bin/env python3
"""
test_phase5_full_flow.py
Phase 5 Integration Test - Full Flow (Cleaned up order)
"""

from economy import (
    generate_pedersen_params,
    AssetManager,
    GameSave,
)
import os
import tempfile


def main():
    print("=== Phase 5 Full Flow Test ===\n")

    params = generate_pedersen_params()
    manager = AssetManager(pedersen_params=params)

    # 1. Mint
    print("1. Minting asset with confidential amount...")
    asset = manager.mint(
        asset_id="test_sword_001",
        pah_path="/pqc_assets/test_sword.pqcasset",
        actor=0,
        amount=1,
        metadata={"name": "Test Sword", "damage": 100}
    )
    print(f"   Minted: {asset.asset_id if asset else 'FAILED'}")

    # 2. Transfer
    print("\n2. Transferring asset to player role...")
    success, msg = manager.transfer("test_sword_001", new_owner_role=5, actor=0)
    print(f"   Transfer successful: {success} ({msg})")

    # 3. Save and load cycle (BEFORE burning)
    print("\n3. Testing save and load cycle...")
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "test_economy.json")
        manager.save_to_file(save_path)

        loaded_manager = AssetManager.load_from_file(save_path, params)
        print(f"   Loaded {len(loaded_manager.assets)} assets after save/load")

    # 4. Burn (after load so we can see the loaded assets count)
    print("\n4. Burning the asset...")
    success, msg = manager.burn("test_sword_001", actor=5)
    print(f"   Burn successful: {success} ({msg})")

    # 5. PQC-signed GameSave
    print("\n5. Creating and PQC-signing GameSave...")
    game_save = GameSave(
        player_id="test_player_01",
        economy_state=manager.to_dict()
    )
    signed_path = game_save.sign_with_pah(algorithm="falcon")

    if signed_path:
        print(f"   Successfully signed save: {signed_path}")
        print(f"   Signature verified: {game_save.verify_with_pah()}")
    else:
        print("   Signing failed (PAH binary might not be available)")

    print("\n=== Phase 5 Full Flow Test Complete ===")


if __name__ == "__main__":
    main()
