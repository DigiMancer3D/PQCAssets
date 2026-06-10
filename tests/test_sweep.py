#!/usr/bin/env python3
"""
New_Thing Phase 0/1 Sweep Test (Updated for current keygen structure)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=== New_Thing Phase 0/1 Sweep Test ===\n")

print("1. Testing core imports...")
try:
    from fusion.fusion_hash import create_transaction, verify_transaction
    from svc.fusionhash_svc_bridge import create_svc_mint_from_kickback, can_participate_in_transfers
    from keygen.unified_sphinx_keygen import generate_key_family
    print("   ✅ All core imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

print("\n2. Testing Rust Bulletproofs backend...")
try:
    import rust_bulletproofs
    print("   ✅ rust_bulletproofs loaded (Rust backend active)")
except ImportError:
    print("   ⚠️  Using Python fallback")

print("\n3. Testing unified key generation...")
try:
    family = generate_key_family(role=0)
    btc = family["families"]["btc"]["standard"]
    bch = family["families"]["bch"]["standard"]
    print(f"   ✅ Key generation works")
    print(f"      BTC: {btc}")
    print(f"      BCH: {bch}")
except Exception as e:
    print(f"   ❌ Key generation failed: {e}")

print("\n4. Testing basic FusionHash transaction...")
try:
    tx = create_transaction(inputs=[("alice", 100000000)], outputs=[("bob", 90000000)], delta=0, fee=10000000)
    print(f"   ✅ create_transaction + verify = {verify_transaction(tx)}")
except Exception as e:
    print(f"   ❌ FusionHash test failed: {e}")

print("\n5. Testing SVC functions...")
try:
    result = create_svc_mint_from_kickback(kickback_amount=25000000, coin_id="TEST-SWEEP", current_total_balance=10.0, enforce_participation_check=False)
    print(f"   ✅ create_svc_mint_from_kickback works → {result['coin_system_data']['coin_id']}")
except Exception as e:
    print(f"   ❌ SVC test failed: {e}")

print("\n=== Sweep Test Complete ===")
