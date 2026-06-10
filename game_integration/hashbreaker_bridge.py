#!/usr/bin/env python3
"""
game_integration/hashbreaker_bridge.py
Bridge between #HASHBREAKER game and Wallet system.

Saves generated .kchain files to the wallets/ folder.
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

from wallet.wallet import Wallet


def create_wallet_from_game_win(
    game_session_id: str,
    score: int,
    level: int,
    debug_used: bool = False,
    requested_role: Optional[int] = None,
    save_directory: str = "wallets"          # ← Changed to wallets/ as requested
) -> Dict[str, Any]:
    """
    Called when player wins or uses a cheat code.
    Creates a Wallet and saves it as a .kchain file.
    """
    # Create deterministic entropy from game data
    entropy_input = f"{game_session_id}:{score}:{level}:{debug_used}".encode()
    seed = hashlib.shake_256(entropy_input).digest(32)

    # Create wallet
    wallet = Wallet(wallet_id=f"hashbreaker_{game_session_id}")
    info = wallet.create(
        seed_method="trinary_dowsing",
        requested_role=requested_role
    )

    # Save as .kchain (compatible format)
    path = wallet.save(directory=save_directory, compatible=True)

    return {
        "wallet_id": wallet.wallet_id,
        "role": info["role"],
        "btc_address": info["btc_address"],
        "bch_address": info["bch_address"],
        "kchain_path": str(path),
        "game_session": game_session_id,
        "score": score,
        "level": level,
        "debug_used": debug_used
    }
