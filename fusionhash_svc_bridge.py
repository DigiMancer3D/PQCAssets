#!/usr/bin/env python3
"""
fusionhash_svc_bridge.py
SVC Bridge – Economic Mechanics v4 (with Cross-Chain Support)
"""
from typing import Optional, Dict, Any, List
import secrets
import time
import sys
from pathlib import Path

# Robust import so this works when called from utils/ or anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fusion.fusion_hash import create_transaction, TransactionMetadata

SVC_CONTRACT_VERSION = "svc-v1"

def _make_svc_metadata(tx_type, coin_id=None, role=None, spx_qec_ref=None, memo="", extra=None):
    meta = TransactionMetadata(
        tx_type=tx_type,
        contract_ref=SVC_CONTRACT_VERSION,
        memo=memo or f"SVC {tx_type}",
        extra=extra or {}
    )
    if coin_id: meta.extra["coin_id"] = coin_id
    if role: meta.extra["role"] = role
    if spx_qec_ref: meta.extra["spx_qec_ref"] = spx_qec_ref
    return meta


# =============================================================================
# Participation & Threshold Helpers (Real Functions)
# =============================================================================

def can_participate_in_transfers(total_svc_balance: float) -> bool:
    """Requires at least 1.9 SVC to help with transfers."""
    return total_svc_balance >= 1.9

def can_transfer_whole_coins(whole_coins_owned: int) -> bool:
    """Requires at least 1 whole SVC coin to transfer coins or specialized boxes."""
    return whole_coins_owned >= 1

def calculate_whole_coins(total_balance: float) -> int:
    return int(total_balance // 1.0)

def can_user_mint_new_coin(current_balance: float, whole_coins: int) -> bool:
    return can_participate_in_transfers(current_balance) and can_transfer_whole_coins(whole_coins)


# =============================================================================
# Simple Helpers
# =============================================================================
def create_svc_issuance(outputs, delta, fee=0, coin_id=None, role=None, spx_qec_ref=None, memo="SVC Issuance", **kwargs):
    metadata = _make_svc_metadata("svc_issuance", coin_id, role, spx_qec_ref, memo, **kwargs)
    return create_transaction(inputs=[], outputs=outputs, delta=delta, fee=fee, metadata=metadata)

def create_svc_redemption(inputs, outputs=None, delta=None, fee=0, coin_id=None, role=None, spx_qec_ref=None, memo="SVC Redemption", **kwargs):
    if outputs is None: outputs = []
    if delta is None:
        delta = -(sum(v for _, v in inputs) - sum(v for _, v in outputs) - fee)
    metadata = _make_svc_metadata("svc_redemption", coin_id, role, spx_qec_ref, memo, **kwargs)
    return create_transaction(inputs=inputs, outputs=outputs, delta=delta, fee=fee, metadata=metadata)

def create_svc_transfer(inputs, outputs, fee=0, coin_id=None, role=None, spx_qec_ref=None, memo="SVC Transfer", **kwargs):
    metadata = _make_svc_metadata("svc_transfer", coin_id, role, spx_qec_ref, memo, **kwargs)
    return create_transaction(inputs=inputs, outputs=outputs, delta=0, fee=fee, metadata=metadata)


# =============================================================================
# Confidential SVC Flows
# =============================================================================
def create_confidential_svc_issuance(amount, fee=0, coin_id=None, role=None, spx_qec_ref=None, memo="Confidential SVC Issuance", **kwargs):
    metadata = _make_svc_metadata("confidential_svc_issuance", coin_id, role, spx_qec_ref, memo, **kwargs)
    return create_transaction(inputs=[], outputs=[], delta=amount, fee=fee, metadata=metadata)

def create_confidential_svc_redemption(amount, fee=0, coin_id=None, role=None, spx_qec_ref=None, memo="Confidential SVC Redemption", **kwargs):
    metadata = _make_svc_metadata("confidential_svc_redemption", coin_id, role, spx_qec_ref, memo, **kwargs)
    return create_transaction(inputs=[], outputs=[], delta=-amount, fee=fee, metadata=metadata)


# =============================================================================
# Core Economic Function: Mint from Kickback + Dust + Key Material
# =============================================================================

def create_svc_mint_from_kickback(
    kickback_amount: int,
    coin_id: str,
    role: str = "treasury",
    spx_qec_ref: Optional[str] = None,
    dust_amount: int = 0,
    key_materials_burned: int = 2,
    key_material_hashes: Optional[List[str]] = None,
    previous_coin_id: Optional[str] = None,
    current_total_balance: Optional[float] = None,
    enforce_participation_check: bool = True,
    memo: str = "Mint from kickback + dust wealth + key material burn",
    extra: Optional[Dict[str, Any]] = None
):
    """
    Enhanced economic minting function for Self-Verifying Coins (SVC).

    Improvements in Phase 2:
    - Tracks kickback_amount + dust_amount + key_materials_burned with proof support
    - Enforces participation rules (can_participate_in_transfers, whole_coins) with clear errors
    - Supports previous_coin_id (ghost coin / kickback reference)
    - Returns richer coin_system_data for coin_system.py integration
    """
    total_mint = kickback_amount + dust_amount

    # === Participation Rule Enforcement ===
    if enforce_participation_check and current_total_balance is not None:
        if not can_participate_in_transfers(current_total_balance):
            raise ValueError(
                f"Participation rule failed: You need at least 1.9 SVC to help with transfers. "
                f"Current balance: {current_total_balance}"
            )

        whole_coins = calculate_whole_coins(current_total_balance)
        if key_materials_burned > 0 and not can_transfer_whole_coins(whole_coins):
            raise ValueError(
                f"Whole coin rule failed: Burning key material requires owning at least 1 whole SVC coin. "
                f"You currently have {whole_coins} whole coin(s)."
            )

    # === Generate SPX-QEC reference if not provided ===
    if spx_qec_ref is None:
        spx_qec_ref = f"spx_qec_{int(time.time())}_{secrets.token_hex(8)}"

    # === Build rich extra metadata ===
    extra = extra or {}
    extra.update({
        "kickback_amount": kickback_amount,
        "dust_amount": dust_amount,
        "key_materials_burned": key_materials_burned,
        "key_material_hashes": key_material_hashes or [],
        "previous_coin_id": previous_coin_id,
        "mint_type": "kickback_dust_burn",
        "whole_coins_at_mint": calculate_whole_coins(current_total_balance) if current_total_balance else 0,
        "minted_at": int(time.time()),
        "has_key_material_proof": bool(key_material_hashes)
    })

    metadata = _make_svc_metadata(
        tx_type="svc_mint_from_kickback",
        coin_id=coin_id,
        role=role,
        spx_qec_ref=spx_qec_ref,
        memo=memo,
        extra=extra
    )

    tx = create_transaction(
        inputs=[],
        outputs=[],
        delta=total_mint,
        fee=0,
        metadata=metadata
    )

    # === Richer data for coin_system.py ===
    coin_system_data = prepare_mint_data_for_coin_system(
        {"transaction": tx, "metadata": metadata},
        coin_id,
        spx_qec_ref
    )
    # Add extra useful fields for coin_system integration
    coin_system_data.update({
        "kickback_amount": kickback_amount,
        "dust_amount": dust_amount,
        "previous_coin_id": previous_coin_id,
        "key_material_hashes": key_material_hashes or [],
        "total_minted": total_mint
    })

    return {
        "transaction": tx,
        "coin_system_data": coin_system_data,
        "metadata": metadata
    }
    """
    Main economic minting function.

    Supports:
    - Kickback + dust wealth accumulation
    - Key material burn mechanic (proofs go into new coin)
    - Optional participation threshold enforcement
    - Future cross-chain / gossip-based value logic
    """
    total_mint = kickback_amount + dust_amount

    if enforce_participation_check and current_total_balance is not None:
        if not can_participate_in_transfers(current_total_balance):
            raise ValueError(
                f"Insufficient balance for participation. Need at least 1.9 SVC. Current: {current_total_balance}"
            )

    if spx_qec_ref is None:
        spx_qec_ref = f"spx_qec_{int(time.time())}_{secrets.token_hex(8)}"

    extra = extra or {}
    extra.update({
        "kickback_amount": kickback_amount,
        "dust_amount": dust_amount,
        "key_materials_burned": key_materials_burned,
        "mint_type": "kickback_dust_burn",
        "whole_coins_at_mint": calculate_whole_coins(current_total_balance) if current_total_balance else 0,
        "minted_at": int(time.time())
    })

    metadata = _make_svc_metadata(
        tx_type="svc_mint_from_kickback",
        coin_id=coin_id,
        role=role,
        spx_qec_ref=spx_qec_ref,
        memo=memo,
        extra=extra
    )

    tx = create_transaction(
        inputs=[],
        outputs=[],
        delta=total_mint,
        fee=0,
        metadata=metadata
    )

    coin_system_data = prepare_mint_data_for_coin_system(
        {"transaction": tx, "metadata": metadata},
        coin_id,
        spx_qec_ref
    )

    return {
        "transaction": tx,
        "coin_system_data": coin_system_data,
        "metadata": metadata
    }


# =============================================================================
# Cross-Chain Wealth Insertion / Atomic-Style Minting (#7)
# =============================================================================

def create_svc_cross_chain_mint(
    amount: int,
    source_chain: str,
    coin_id: str,
    role: str = "treasury",
    spx_qec_ref: Optional[str] = None,
    cross_chain_proof: Optional[str] = None,
    memo: str = "Cross-chain wealth insertion mint",
    extra: Optional[Dict[str, Any]] = None
):
    """
    Supports cross-chain wealth insertion (one of the stated use cases for SVC minting).

    This can represent atomic-swap style or direct wealth transfer from another chain
    into the SVC system via confidential minting.

    Future enhancements:
    - Validate cross_chain_proof
    - Record source chain + proof in the new coin's metadata / hypertree
    """
    if spx_qec_ref is None:
        spx_qec_ref = f"spx_qec_crosschain_{int(time.time())}_{secrets.token_hex(6)}"

    extra = extra or {}
    extra.update({
        "source_chain": source_chain,
        "cross_chain_proof": cross_chain_proof,
        "mint_type": "cross_chain_insertion",
        "minted_at": int(time.time())
    })

    metadata = _make_svc_metadata(
        tx_type="svc_cross_chain_mint",
        coin_id=coin_id,
        role=role,
        spx_qec_ref=spx_qec_ref,
        memo=memo,
        extra=extra
    )

    tx = create_transaction(
        inputs=[],
        outputs=[],
        delta=amount,
        fee=0,
        metadata=metadata
    )

    return {
        "transaction": tx,
        "metadata": metadata
    }


# =============================================================================
# Integration Helper (Real Function)
# =============================================================================

def prepare_mint_data_for_coin_system(mint_result: dict, coin_id: str, spx_qec_ref: str) -> Dict[str, Any]:
    """Prepares rich structured data to pass to coin_system.py after minting."""
    meta = mint_result.get("metadata", {})
    extra = meta.extra if hasattr(meta, "extra") else meta.get("extra", {})

    return {
        "coin_id": coin_id,
        "spx_qec_ref": spx_qec_ref,
        "mint_tx": str(mint_result.get("transaction", "")),
        "mint_type": extra.get("mint_type", "unknown"),
        "key_materials_burned": extra.get("key_materials_burned", 0),
        "key_material_hashes": extra.get("key_material_hashes", []),
        "previous_coin_id": extra.get("previous_coin_id"),
        "kickback_amount": extra.get("kickback_amount", 0),
        "dust_amount": extra.get("dust_amount", 0),
        "extra": extra or {}
    }
