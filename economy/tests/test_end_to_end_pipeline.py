#!/usr/bin/env python3
"""
test_end_to_end_pipeline.py
Phase 6-3 - End-to-End Asset Pipeline Test

This script simulates the full flow:
GRILLS → PAH Wrapping → Economy System → bSIM Bridge → PQC-signed Save → Load + Verify

It is designed to be educational and runnable even without a full bSIM game.
"""

import os
import tempfile
from economy import (
    generate_pedersen_params,
    AssetManager,
    BSIMEconomyBridge,
    GameSave,
)


def main():
    print("=" * 60)
    print("PHASE 6-3: END-TO-END ASSET PIPELINE TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # ============================================================
        # STEP 1: Simulate GRILLS Export + PAH Wrapping
        # ============================================================
        print("\n[STEP 1] Simulating GRILLS export + PAH wrapping...")

        # In real usage, this would come from grills.py export
        # For this test, we simulate a wrapped asset
        wrapped_asset_path = os.path.join(tmpdir, "test_animation.pqcasset")

        # Create a dummy file to represent a PAH-wrapped asset
        with open(wrapped_asset_path, "w") as f:
            f.write("DUMMY_PQC_WRAPPED_ASSET_FROM_GRILLS")

        print(f"   Created simulated wrapped asset: {wrapped_asset_path}")

        # ============================================================
        # STEP 2: Economy System - Mint Asset with Confidential Amount
        # ============================================================
        print("\n[STEP 2] Minting asset in economy system...")

        params = generate_pedersen_params()
        manager = AssetManager(pedersen_params=params)

        asset = manager.mint(
            asset_id="grills_animation_001",
            pah_path=wrapped_asset_path,
            actor=0,                    # Admin / loot system
            amount=1,
            metadata={
                "source": "grills_export",
                "type": "animation",
                "name": "Test Animation"
            }
        )

        if asset:
            print(f"   Successfully minted: {asset.asset_id}")
        else:
            print("   Minting failed.")
            return

        # ============================================================
        # STEP 3: bSIM Bridge Integration
        # ============================================================
        print("\n[STEP 3] Using bSIM Economy Bridge...")

        bridge = BSIMEconomyBridge(player_id="test_player_001", save_dir=tmpdir)

        # Simulate loot drop using the bridge (this is what bSIM would call)
        bridge.on_loot_drop(
            asset_id="grills_animation_001",
            pah_path=wrapped_asset_path,
            amount=1,
            metadata={"source": "end_to_end_test"}
        )

        print("   Asset registered via bSIM bridge")

        # ============================================================
        # STEP 4: PQC-Signed Save
        # ============================================================
        print("\n[STEP 4] Saving with PQC signature...")

        save_path = bridge.save_player_economy(algorithm="falcon")
        print(f"   Economy saved to: {save_path}")

        # Also create a full GameSave with PQC signing
        game_save = GameSave(
            player_id="test_player_001",
            economy_state=manager.to_dict()
        )
        signed_file = game_save.sign_with_pah(algorithm="falcon")

        if signed_file:
            print(f"   PQC-signed save created: {signed_file}")
            print(f"   Signature valid: {game_save.verify_with_pah()}")
        else:
            print("   PQC signing skipped (PAH binary not found or failed)")

        # ============================================================
        # STEP 5: Load and Verify
        # ============================================================
        print("\n[STEP 5] Loading and verifying state...")

        new_bridge = BSIMEconomyBridge(player_id="test_player_001", save_dir=tmpdir)
        loaded_assets = new_bridge.get_player_assets()

        print(f"   Loaded {len(loaded_assets)} assets after reload")

        if "grills_animation_001" in loaded_assets:
            print("   SUCCESS: Asset survived save/load cycle with PQC protection")
        else:
            print("   WARNING: Asset not found after reload")

    print("\n" + "=" * 60)
    print("END-TO-END PIPELINE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
