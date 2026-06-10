#!/usr/bin/env python3
"""
bSIM_integration_guide.py
Phase 5.3 - Simple Integration Guide for bSIM

This file is designed to be as easy to use as possible.

INSTRUCTIONS:
1. Copy this entire file into your bSIM project folder.
2. At the top of your main game files (or a central file), add:
      from bSIM_integration_guide import get_bridge, on_loot_drop, on_consume_item, etc.

3. Then call the functions from your existing code when these events happen.

You do NOT need to understand all the code below.
Just use the functions at the bottom.
"""

from economy import BSIMEconomyBridge

# This dictionary keeps track of each player's economy bridge
# You don't need to touch this
_player_bridges = {}


def get_bridge(player_id: str):
    """
    This is the most important function.
    It gives you the economy system for a specific player.
    
    Usage:
        bridge = get_bridge("player_123")
    """
    if player_id not in _player_bridges:
        _player_bridges[player_id] = BSIMEconomyBridge(player_id=player_id)
    return _player_bridges[player_id]


# ============================================================
# SIMPLE FUNCTIONS YOU CAN CALL FROM bSIM
# ============================================================

def on_loot_drop(player_id: str, asset_id: str, pah_path: str, amount: int = 1):
    """
    Call this when a player gets loot (from killing enemies, opening chests, quests, etc.)
    
    Example:
        on_loot_drop(player.id, "rare_sword_01", "/pqc_assets/loot/rare_sword.pqcasset")
    """
    bridge = get_bridge(player_id)
    bridge.on_loot_drop(
        asset_id=asset_id,
        pah_path=pah_path,
        amount=amount
    )


def on_consume_item(player_id: str, asset_id: str):
    """
    Call this when a player uses or consumes an item.
    
    Example:
        on_consume_item(player.id, "health_potion_05")
    """
    bridge = get_bridge(player_id)
    bridge.on_consume_item(asset_id=asset_id)


def on_player_trade(from_player_id: str, asset_id: str, to_role: int = 5):
    """
    Call this when a player trades or gives an item to someone else.
    
    Example:
        on_player_trade(player.id, "legendary_sword_42", new_owner_role=5)
    """
    bridge = get_bridge(from_player_id)
    bridge.on_player_trade(
        asset_id=asset_id,
        new_owner_role=to_role
    )


def save_player_game(player_id: str):
    """
    Call this when the player logs out, or when you want to save their progress.
    
    Example:
        save_player_game(player.id)
    """
    bridge = get_bridge(player_id)
    bridge.save_player_economy()


def load_player_game(player_id: str):
    """
    Call this when a player logs in.
    
    Example:
        load_player_game(player.id)
    """
    bridge = get_bridge(player_id)
    bridge.load_player_economy()


# ============================================================
# HOW TO USE THIS IN bSIM (Copy these examples)
# ============================================================

"""
EXAMPLE 1: When an enemy dies and drops loot
------------------------------------------------
In your enemy death code, add something like this:

    if enemy.drops_item:
        on_loot_drop(
            player_id = player.id,
            asset_id = f"{enemy.type}_loot",
            pah_path = "/pqc_assets/loot/" + enemy.loot_file
        )


EXAMPLE 2: When a player uses a consumable item
------------------------------------------------
In your item use function:

    if item.is_consumable:
        on_consume_item(player_id=player.id, asset_id=item.asset_id)
        # Then apply the game effect (heal, buff, etc.)


EXAMPLE 3: When saving the game (on logout or checkpoint)
------------------------------------------------
    save_player_game(player_id=player.id)


EXAMPLE 4: When loading a player (on login)
------------------------------------------------
    load_player_game(player_id=player.id)
"""

print("bSIM Integration Guide loaded. Use the functions above in your game code.")
