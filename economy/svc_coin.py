#!/usr/bin/env python3
"""
economy/svc_coin.py
Phase 5.4 - SVC (Self-Verifying Coin) Mechanics

Basic mechanics for the in-game / on-chain SVC economy:
- Total supply tracking
- Role-controlled minting (only certain roles can increase supply)
- Burn mechanics (reduces supply)
- Simple inflation / role governance hooks
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class SVCCoin:
    """
    Represents the SVC coin itself (separate from individual PQCAssets).
    Tracks global supply and role-based minting rules.
    """
    symbol: str = "SVC"
    total_supply: int = 0
    max_supply: int = 21_000_000          # Example hard cap (can be changed)
    mint_roles: list[int] = field(default_factory=lambda: [0])  # Only role 0 can mint by default
    burn_roles: list[int] = field(default_factory=lambda: [0, 5])

    def can_mint(self, role: int) -> bool:
        return role in self.mint_roles or role == 0

    def can_burn(self, role: int) -> bool:
        return role in self.burn_roles or role == 0

    def mint(self, amount: int, actor_role: int) -> bool:
        if not self.can_mint(actor_role):
            print(f"[SVCCoin] Mint denied for role {actor_role}")
            return False
        if self.total_supply + amount > self.max_supply:
            print(f"[SVCCoin] Mint would exceed max supply")
            return False
        self.total_supply += amount
        print(f"[SVCCoin] Minted {amount} SVC. New supply: {self.total_supply}")
        return True

    def burn(self, amount: int, actor_role: int) -> bool:
        if not self.can_burn(actor_role):
            print(f"[SVCCoin] Burn denied for role {actor_role}")
            return False
        if amount > self.total_supply:
            amount = self.total_supply
        self.total_supply -= amount
        print(f"[SVCCoin] Burned {amount} SVC. New supply: {self.total_supply}")
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "total_supply": self.total_supply,
            "max_supply": self.max_supply,
            "mint_roles": self.mint_roles,
            "burn_roles": self.burn_roles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SVCCoin":
        return cls(
            symbol=data.get("symbol", "SVC"),
            total_supply=data.get("total_supply", 0),
            max_supply=data.get("max_supply", 21_000_000),
            mint_roles=data.get("mint_roles", [0]),
            burn_roles=data.get("burn_roles", [0, 5]),
        )
