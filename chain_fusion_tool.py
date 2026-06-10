#!/usr/bin/env python3
"""
chain_fusion_tool.py
Complete CLI tool for FusionHash + SVC with file support
"""

import sys
import argparse
import json
import os
from pathlib import Path

# =============================================================================
# Robust Project Root Detection (This fixes the ModuleNotFoundError)
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# Correct Package Imports
# =============================================================================
from fusion.fusion_hash import create_transaction, TransactionMetadata, verify_transaction
from svc.fusionhash_svc_bridge import (
    create_svc_issuance,
    create_svc_redemption,
    create_svc_transfer,
    create_confidential_svc_issuance,
    create_confidential_svc_redemption,
    create_svc_mint_from_kickback,
    can_participate_in_transfers,
    calculate_whole_coins,
)


# =============================================================================
# Transaction Templates (kept from your original)
# =============================================================================
ALL_TEMPLATES = {
    "simple_payment": "Simple payment between two parties",
    "burn": "Burn funds (reduce supply)",
    "mint": "Mint new funds",
    "batch_settlement": "Batch settlement of multiple transfers",
    "svc_issuance": "Issue new SVC coins",
    "svc_redemption": "Redeem SVC coins",
    "svc_transfer": "Transfer SVC coins",
    "svc_mint_from_kickback": "Mint SVC from kickback + dust (main economic flow)",
}


def load_transaction_from_file(filepath: str):
    """Load a transaction from a JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data


def main():
    parser = argparse.ArgumentParser(description="FusionHash Transaction Tool")
    parser.add_argument("--create-transaction", action="store_true", help="Create a new transaction")
    parser.add_argument("--template", type=str, help="Template to use")
    parser.add_argument("--tx-file", type=str, help="Load transaction from JSON file")
    parser.add_argument("--amount", type=int, default=0)
    parser.add_argument("--fee", type=int, default=1000)
    parser.add_argument("--kickback-amount", type=int, default=0)
    parser.add_argument("--dust-amount", type=int, default=0)
    parser.add_argument("--coin-id", type=str, default=None)
    parser.add_argument("--role", type=int, default=0)
    parser.add_argument("--spx-qec-ref", type=str, default=None)

    args = parser.parse_args()

    if args.tx_file:
        tx_data = load_transaction_from_file(args.tx_file)
        print("Loaded transaction from file:")
        print(json.dumps(tx_data, indent=2))
        return

    if args.create_transaction:
        if not args.template:
            print("Error: --template is required when using --create-transaction")
            print("Available templates:", list(ALL_TEMPLATES.keys()))
            return

        print(f"Creating transaction using template: {args.template}")

        if args.template == "svc_mint_from_kickback":
            result = create_svc_mint_from_kickback(
                kickback_amount=args.kickback_amount or 25000000,
                dust_amount=args.dust_amount or 5000000,
                coin_id=args.coin_id or "SVC-MINT-TEST",
                current_total_balance=10.0,
                role=args.role,
                spx_qec_ref=args.spx_qec_ref,
                enforce_participation_check=False
            )
            print("\n✅ Transaction created successfully!")
            print(json.dumps(result, indent=2, default=str))

        else:
            # Basic FusionHash transaction
            tx = create_transaction(
                inputs=[("sender", args.amount + args.fee)],
                outputs=[("receiver", args.amount)],
                delta=0,
                fee=args.fee
            )
            print("\n✅ Basic transaction created:")
            print(json.dumps(tx, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
