#!/usr/bin/env python3
"""
economy/asset.py
Phase 5.2 / 6.1 - PQC Asset + Mint/Burn/Transfer System + Role Permissions
With logging and input validation + improved error handling (Phase 6)
"""

from __future__ import annotations
import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from .pedersen import PedersenParams, PedersenCommitment, generate_pedersen_params
from .roles_integration import can_mint, can_burn, can_transfer, get_role


# ====================== LOGGER SETUP ======================
logger = logging.getLogger(__name__)
# ========================================================


ROLE_ADMIN = 0
ROLE_PLAYER = 5
ROLE_VIEWER = 9


@dataclass
class PQCAsset:
    asset_id: str
    pah_path: str
    owner_role: int = ROLE_PLAYER
    amount_commitment: Optional[PedersenCommitment] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def has_confidential_amount(self) -> bool:
        return self.amount_commitment is not None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "asset_id": self.asset_id,
            "pah_path": self.pah_path,
            "owner_role": self.owner_role,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
        if self.amount_commitment:
            data["amount_commitment"] = self.amount_commitment.to_bytes().hex()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], params: PedersenParams) -> "PQCAsset":
        asset = cls(
            asset_id=data["asset_id"],
            pah_path=data["pah_path"],
            owner_role=data.get("owner_role", ROLE_PLAYER),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
        )
        if "amount_commitment" in data:
            asset.amount_commitment = PedersenCommitment.from_bytes(
                params, bytes.fromhex(data["amount_commitment"])
            )
        return asset


class AssetManager:
    def __init__(self, pedersen_params: Optional[PedersenParams] = None):
        self.params = pedersen_params or generate_pedersen_params()
        self.assets: Dict[str, PQCAsset] = {}
        logger.info("AssetManager initialized")

    # ---------------------- Validation Helpers ----------------------
    def _validate_amount(self, amount: Optional[int]) -> bool:
        if amount is not None and amount < 0:
            logger.warning(f"Invalid negative amount attempted: {amount}")
            return False
        return True

    def _validate_asset_id(self, asset_id: str) -> bool:
        if not asset_id or not isinstance(asset_id, str):
            logger.warning(f"Invalid asset_id: {asset_id}")
            return False
        return True

    # ---------------------- Role Checks ----------------------
    def _check_mint(self, actor: Any) -> bool:
        return can_mint(actor)

    def _check_burn(self, actor: Any, asset_owner_role: int) -> bool:
        return can_burn(actor, asset_owner_role)

    def _check_transfer(self, actor: Any, asset_owner_role: int) -> bool:
        return can_transfer(actor, asset_owner_role)

    # ---------------------- Core Operations ----------------------
    def mint(
        self,
        asset_id: str,
        pah_path: str,
        actor: Any = 0,
        amount: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[PQCAsset]:
        if not self._validate_asset_id(asset_id):
            return None
        if not self._validate_amount(amount):
            return None
        if not self._check_mint(actor):
            role = get_role(actor)
            logger.warning(f"Mint denied for role {role} on asset {asset_id}")
            return None
        if asset_id in self.assets:
            logger.warning(f"Duplicate asset ID attempted: {asset_id}")
            return None

        commitment = None
        if amount is not None:
            blinding = os.urandom(32)
            commitment = PedersenCommitment.commit(self.params, value=amount, blinding=blinding)

        asset = PQCAsset(
            asset_id=asset_id,
            pah_path=pah_path,
            owner_role=get_role(actor),
            amount_commitment=commitment,
            metadata=metadata or {},
        )
        self.assets[asset_id] = asset
        logger.info(f"Minted asset: {asset_id} (amount={amount})")
        return asset

    def burn(self, asset_id: str, actor: Any) -> Tuple[bool, str]:
        """
        Returns (success: bool, message: str)
        """
        if asset_id not in self.assets:
            msg = f"Asset not found: {asset_id}"
            logger.warning(msg)
            return False, msg

        owner_role = self.assets[asset_id].owner_role
        if not self._check_burn(actor, owner_role):
            msg = (
                f"Burn denied. Actor (role {get_role(actor)}) does not have permission "
                f"to burn this asset (owned by role {owner_role})."
            )
            logger.warning(msg)
            return False, msg

        del self.assets[asset_id]
        logger.info(f"Burned asset: {asset_id}")
        return True, f"Successfully burned {asset_id}"

    def transfer(self, asset_id: str, new_owner_role: int, actor: Any) -> Tuple[bool, str]:
        if asset_id not in self.assets:
            return False, f"Asset not found: {asset_id}"
        asset = self.assets[asset_id]
        if not self._check_transfer(actor, asset.owner_role):
            return False, "Transfer denied due to insufficient permissions."

        asset.owner_role = new_owner_role
        logger.info(f"Transferred {asset_id} to role {new_owner_role}")
        return True, f"Transferred {asset_id}"

    # ---------------------- Save / Load ----------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "assets": {aid: a.to_dict() for aid, a in self.assets.items()},
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_to_file(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved economy state to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str, params: Optional[PedersenParams] = None) -> "AssetManager":
        with open(filepath, "r") as f:
            data = json.load(f)

        manager = cls(pedersen_params=params)
        for aid, asset_data in data.get("assets", {}).items():
            manager.assets[aid] = PQCAsset.from_dict(asset_data, manager.params)
        logger.info(f"Loaded {len(manager.assets)} assets from {filepath}")
        return manager
