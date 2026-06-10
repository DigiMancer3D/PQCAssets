#!/usr/bin/env python3
"""
test_bsim_bridge.py
Phase 5.3 - BSIMEconomyBridge Test

Tests the main integration bridge used by bSIM.
"""

from economy import BSIMEconomyBridge
import tempfile
import os


def main():
    print("=== BSIMEconomyBridge Test ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create bridge for a test player
        bridge = BSIMEconomyBridge(player_id="test_player_42", save_dir=tmpdir)

        # 1. Simulate loot drop
        print("1. Simulating loot drop...")
        asset = bridge.on_loot_drop(
            asset_id="bridge_test_sword",
            pah_path="/pqc_assets/test_sword.pqcasset",
            amount=1,
            metadata={"source": "test_loot"}
        )
        print(f"   Loot received: {asset.asset_id if asset else 'None'}")

        # 2. Simulate item consumption
        print("\n2. Simulating item consumption...")
        success = bridge.on_consume_item("bridge_test_sword")
        print(f"   Consumption successful: {success}")

        # 3. Save state
        print("\n3. Saving player economy...")
        bridge.save_player_economy(algorithm="falcon")

        # 4. Create new bridge and load
        print("\n4. Creating new bridge and loading state...")
        new_bridge = BSIMEconomyBridge(player_id="test_player_42", save_dir=tmpdir)
        assets = new_bridge.get_player_assets()
        print(f"   Loaded {len(assets)} assets after reload")

    print("\n=== BSIMEconomyBridge Test Complete ===")


if __name__ == "__main__":
    main()
