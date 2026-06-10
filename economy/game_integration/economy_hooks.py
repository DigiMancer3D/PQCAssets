#!/usr/bin/env python3
"""
game_integration/economy_hooks.py
Real bSIM Integration Layer (Complete Version)

This file makes it easy to connect the economy system to your game.
You only need to use the functions at the bottom of this file.

Usage:
    from game_integration.economy_hooks import (
        player_receives_loot,
        player_uses_item,
        save_player_economy,
        load_player_economy,
        player_has_item,
        get_player_items
    )
"""

from economy import BSIMEconomyBridge
from typing import Optional, Dict, Any

# ============================================================
# INTERNAL - You usually don't need to touch this
# ============================================================

_player_bridges: Dict[str, BSIMEconomyBridge] = {}


def get_economy(player_id: str) -> BSIMEconomyBridge:
    """Get or create the economy system for a specific player."""
    if player_id not in _player_bridges:
        _player_bridges[player_id] = BSIMEconomyBridge(player_id=player_id)
    return _player_bridges[player_id]


# ============================================================
# PUBLIC FUNCTIONS - Use these in your game code
# ============================================================

def player_receives_loot(
    player_id: str,
    item_name: str,
    wrapped_file_path: str,
    amount: Optional[int] = None,
    extra_info: Optional[Dict] = None
):
    """
    Call this when a player receives an item from loot, chests, quests, etc.
    """
    economy = get_economy(player_id)
    economy.on_loot_drop(
        asset_id=item_name,
        pah_path=wrapped_file_path,
        amount=amount,
        metadata=extra_info
    )


def player_uses_item(player_id: str, item_name: str) -> bool:
    """
    Call this when a player consumes or uses an item.
    Returns True if the item was successfully consumed.
    """
    economy = get_economy(player_id)
    return economy.on_consume_item(item_name)


def player_trades_item(
    from_player_id: str,
    item_name: str,
    to_player_role: int = 5
) -> bool:
    """
    Call this when a player gives or trades an item to someone else.
    """
    economy = get_economy(from_player_id)
    return economy.on_player_trade(item_name, to_player_role)


def save_player_economy(player_id: str):
    """Call this when you want to save the player's economy state."""
    economy = get_economy(player_id)
    economy.save_player_economy()


def load_player_economy(player_id: str):
    """Call this when loading a player's economy (usually on login)."""
    economy = get_economy(player_id)
    economy.load_player_economy()


def get_player_items(player_id: str) -> Dict[str, Any]:
    """Returns all items the player currently owns."""
    economy = get_economy(player_id)
    return economy.get_player_assets()


def player_has_item(player_id: str, item_name: str) -> bool:
    """Check if a player owns a specific item."""
    items = get_player_items(player_id)
    return item_name in items


def get_item_count(player_id: str, item_name: str) -> int:
    """Get how many of a specific item the player has (if tracked)."""
    items = get_player_items(player_id)
    if item_name in items:
        # You can expand this later if you track quantities
        return 1
    return 0


def initialize_player_economy(player_id: str):
    """
    Optional: Call this when a new player is created
    to make sure their economy system is ready.
    """
    get_economy(player_id)
    print(f"[Economy] Initialized economy for new player: {player_id}")
