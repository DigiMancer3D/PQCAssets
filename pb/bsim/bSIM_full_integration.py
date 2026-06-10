#!/usr/bin/env python3
"""
bSIM_full_integration.py
Phase 6-2 - Full bSIM Integration (Simple Version)

This file is designed to be the easiest possible way to connect
the economy system into your bSIM game.

INSTRUCTIONS:
1. Copy this file into your bSIM project folder.
2. At the top of your main game files, add:
      from bSIM_full_integration import economy

3. Then use the simple functions below when things happen in your game.

You only need to use the functions at the bottom of this file.
"""

from economy import BSIMEconomyBridge

# This stores one bridge per player
_bridges = {}


def get_economy(player_id: str):
    """
    Get the economy system for a player.
    This is the main function you will use.
    """
    if player_id not in _bridges:
        _bridges[player_id] = BSIMEconomyBridge(player_id=player_id)
    return _bridges[player_id]


# ============================================================
# SIMPLE FUNCTIONS TO USE IN bSIM
# ============================================================

def player_gets_loot(player_id: str, item_name: str, wrapped_file_path: str):
    """
    Call this when a player receives an item from loot.
    
    Example:
        player_gets_loot(player.id, "rare_sword", "/pqc_assets/loot/rare_sword.pqcasset")
    """
    economy = get_economy(player_id)
    economy.on_loot_drop(
        asset_id=item_name,
        pah_path=wrapped_file_path,
        amount=1
    )


def player_uses_item(player_id: str, item_name: str):
    """
    Call this when a player uses or consumes an item.
    
    Example:
        player_uses_item(player.id, "health_potion")
    """
    economy = get_economy(player_id)
    economy.on_consume_item(item_name)


def player_trades_item(from_player_id: str, item_name: str, to_player_role: int = 5):
    """
    Call this when a player gives or trades an item.
    
    Example:
        player_trades_item(player.id, "legendary_sword", new_owner_role=5)
    """
    economy = get_economy(from_player_id)
    economy.on_player_trade(item_name, to_player_role)


def save_player_progress(player_id: str):
    """
    Call this when you want to save the player's economy state.
    
    Example:
        save_player_progress(player.id)
    """
    economy = get_economy(player_id)
    economy.save_player_economy()


def load_player_progress(player_id: str):
    """
    Call this when a player logs in or loads their character.
    
    Example:
        load_player_progress(player.id)
    """
    economy = get_economy(player_id)
    economy.load_player_economy()


# ============================================================
# HOW TO USE THIS IN YOUR GAME (Copy these examples)
# ============================================================

"""
EXAMPLE 1: When a player kills an enemy and gets loot
------------------------------------------------------
In your enemy death function, add:

    if enemy.has_loot:
        player_gets_loot(
            player_id = player.id,
            item_name = enemy.loot_item_name,
            wrapped_file_path = "/pqc_assets/loot/" + enemy.loot_file
        )


EXAMPLE 2: When a player uses a consumable item
------------------------------------------------
In your item use code:

    if item.is_consumable:
        player_uses_item(player_id=player.id, item_name=item.name)
        # Then apply the actual game effect (heal, buff, etc.)


EXAMPLE 3: When saving the game
-------------------------------
In your save / logout function:

    save_player_progress(player_id=player.id)


EXAMPLE 4: When loading a player
--------------------------------
In your login or character load function:

    load_player_progress(player_id=player.id)
"""

print("bSIM Full Integration loaded successfully.")
print("Use the functions above in your game code.")