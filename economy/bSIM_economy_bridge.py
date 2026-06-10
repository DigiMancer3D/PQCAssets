#!/usr/bin/env python3
"""
economy/bSIM_economy_bridge.py
Phase 5.3 / 6.2 - bSIM Economy Integration Bridge
With improved permission handling on loot drops
"""

from __future__ import annotations
import os
import json
import logging
from typing import Optional, Dict, Any

from .asset import AssetManager, PQCAsset, ROLE_PLAYER, ROLE_ADMIN
from .save_format import GameSave
from .pedersen import generate_pedersen_params


# ====================== LOGGER SETUP ======================
logger = logging.getLogger(__name__)
# ========================================================


class BSIMEconomyBridge:
    def __init__(self, player_id: str, save_dir: str = "saves"):
        self.player_id = player_id
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

        self.params = generate_pedersen_params()
        self.manager = AssetManager(pedersen_params=self.params)
        self._load_state()

    def on_loot_drop(
        self,
        asset_id: str,
        pah_path: str,
        amount: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[PQCAsset]:
        logger.info(f"Loot drop for {self.player_id}: {asset_id}")

        asset = self.manager.mint(
            asset_id=asset_id,
            pah_path=pah_path,
            actor=ROLE_ADMIN,
            amount=amount,
            metadata=metadata or {"source": "loot_drop"}
        )

        # Auto-assign ownership to the receiving player
        if asset:
            asset.owner_role = ROLE_PLAYER
            logger.info(f"Auto-assigned ownership of {asset_id} to player")

        return asset

    def on_player_trade(
        self,
        asset_id: str,
        new_owner_role: int,
        actor_role: int = ROLE_PLAYER,
    ) -> bool:
        logger.info(f"Trade request: {asset_id} → role {new_owner_role}")
        success, _ = self.manager.transfer(asset_id, new_owner_role, actor=actor_role)
        return success

    def on_consume_item(self, asset_id: str, actor_role: int = ROLE_PLAYER) -> bool:
        success, message = self.manager.burn(asset_id, actor=actor_role)
        if not success:
            logger.warning(message)
        return success

    def save_player_economy(self, algorithm: str = "falcon") -> str:
        filename = os.path.join(self.save_dir, f"{self.player_id}_economy.json")
        self.manager.save_to_file(filename)

        game_save = GameSave(
            player_id=self.player_id,
            economy_state=self.manager.to_dict(),
        )
        game_save.sign_with_pah(algorithm=algorithm)

        save_path = os.path.join(self.save_dir, f"{self.player_id}_gamesave.json")
        with open(save_path, "w") as f:
            json.dump(game_save.to_dict(), f, indent=2)

        logger.info(f"Economy saved for {self.player_id}")
        return filename

    def load_player_economy(self) -> bool:
        filename = os.path.join(self.save_dir, f"{self.player_id}_economy.json")
        if os.path.exists(filename):
            self.manager = AssetManager.load_from_file(filename, self.params)
            logger.info(f"Economy loaded for {self.player_id}")
            return True
        logger.info(f"No existing economy save for {self.player_id}")
        return False

    def _load_state(self):
        self.load_player_economy()

    def get_player_assets(self) -> Dict[str, PQCAsset]:
        return self.manager.assets

    def get_asset(self, asset_id: str) -> Optional[PQCAsset]:
        return self.manager.assets.get(asset_id)
