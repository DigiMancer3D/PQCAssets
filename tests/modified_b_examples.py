#!/usr/bin/env python3
"""
Modified B Examples - Unified Transaction Handling

Demonstrates balanced, unbalanced (with burning), batched multi-party,
and transactions with rich metadata (op_return, contract_ref, etc.).
"""

from fusion_hash import create_transaction, TransactionMetadata, verify_transaction

print("=== Modified B Examples ===\n")

# ============================================================
# Example 1: Balanced Transaction (delta = 0)
# ============================================================
print("Example 1: Balanced Transaction")
tx1 = create_transaction(
    inputs=[("alice", 100000000), ("bob", 50000000)],
    outputs=[("charlie", 150000000)],
    delta=0,
    fee=2000000,
    fee_buffer=1.0/3,
    metadata=TransactionMetadata(
        tx_type="payment",
        batch_id="batch_001",
        memo="Simple balanced payment"
    )
)
print(f"  Created: {tx1.string[:40]}...")
print(f"  Delta match: {verify_transaction(tx1)}")
if isinstance(tx1.metadata, dict):
    print(f"    logical_net: {tx1.metadata.get('logical_net')}")
    print(f"    delta: {tx1.metadata.get('delta')}")
    print(f"    delta_match (stored): {tx1.metadata.get('delta_match')}")
print()

# ============================================================
# Example 2: Unbalanced with Burning (negative delta)
# ============================================================
print("Example 2: Unbalanced Transaction with Burning")
tx2 = create_transaction(
    inputs=[("alice", 200000000)],
    outputs=[("bob", 120000000)],
    delta=-80000000,           # Burning 80M
    fee=3000000,
    fee_buffer=1.0/3,
    metadata=TransactionMetadata(
        tx_type="burn",
        contract_ref="contract_burn_v1",
        op_return="Burning tokens as per contract rules",
        memo="Token burn transaction"
    )
)
print(f"  Created: {tx2.string[:40]}...")
print(f"  Delta match: {verify_transaction(tx2)}")
if isinstance(tx2.metadata, dict):
    print(f"    logical_net: {tx2.metadata.get('logical_net')}")
    print(f"    delta: {tx2.metadata.get('delta')}")
    print(f"    delta_match (stored): {tx2.metadata.get('delta_match')}")
print()

# ============================================================
# Example 3: Multi-party Batched Transaction
# ============================================================
print("Example 3: Multi-party Batched Transaction")
tx3 = create_transaction(
    inputs=[
        ("alice", 30000000),
        ("bob", 45000000),
        ("carol", 25000000)
    ],
    outputs=[
        ("dave", 50000000),
        ("eve", 50000000)
    ],
    delta=0,
    fee=4000000,
    fee_buffer=1.0/3,
    metadata=TransactionMetadata(
        tx_type="batch_settlement",
        batch_id="batch_settlement_2026_06",
        memo="Multi-party batch settlement"
    )
)
print(f"  Created: {tx3.string[:40]}...")
print(f"  Delta match: {verify_transaction(tx3)}")
if isinstance(tx3.metadata, dict):
    print(f"    logical_net: {tx3.metadata.get('logical_net')}")
    print(f"    delta: {tx3.metadata.get('delta')}")
    print(f"    delta_match (stored): {tx3.metadata.get('delta_match')}")
print()

# ============================================================
# Example 4: Contract Call with op_return + positive delta (mint)
# ============================================================
print("Example 4: Contract Call with Minting (positive delta)")
tx4 = create_transaction(
    inputs=[],                          # Pure mint (no real inputs)
    outputs=[("user1", 1000000000)],
    delta=1000000000,                   # Minting new tokens
    fee=10000000,
    fee_buffer=1.0/3,
    metadata=TransactionMetadata(
        tx_type="contract_call",
        contract_ref="0xdef456_mint_contract",
        op_return="Mint 1B tokens to user1",
        memo="Governance-approved mint"
    )
)
print(f"  Created: {tx4.string[:40]}...")
print(f"  Delta match: {verify_transaction(tx4)}")
if isinstance(tx4.metadata, dict):
    print(f"    logical_net: {tx4.metadata.get('logical_net')}")
    print(f"    delta: {tx4.metadata.get('delta')}")
    print(f"    delta_match (stored): {tx4.metadata.get('delta_match')}")
print()

print("🎉 All Modified B examples completed successfully!")
print("   You can now use create_transaction() for real off-chain transaction processing.")
