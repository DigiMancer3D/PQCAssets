#!/usr/bin/env python3
"""
wallet/wallet.py
Phase 2 Wallet Class - Improved .kchain Compatibility
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

from keygen.unified_sphinx_keygen import generate_key_family
from seeds import generate_auto_seed, generate_trinary_dowsing_seed, generate_solar_trinary_seed
from roles.role_system import assign_role, get_role_capabilities


class Wallet:
    def __init__(self, wallet_id: Optional[str] = None):
        self.wallet_id = wallet_id or f"wallet_{int(time.time())}"
        self.key_material: Optional[Dict] = None
        self.role: int = 5
        self.role_info: Dict = {}
        self.created_at = int(time.time())
        self.path: Optional[Path] = None

    def create(self, seed_method: str = "auto", seed_data: Any = None,
               requested_role: Optional[int] = None, use_cashaddr: bool = True) -> Dict[str, Any]:
        self.role = assign_role(requested_role)
        self.role_info = get_role_capabilities(self.role)

        if seed_method == "auto":
            seed = generate_auto_seed()
        elif seed_method == "trinary_dowsing":
            seed = generate_trinary_dowsing_seed()
        elif seed_method == "solar_smt32":
            if seed_data is None:
                raise ValueError("seed_data is required for solar_smt32")
            seed = generate_solar_trinary_seed(seed_data)
        elif seed_method == "user_secret":
            if seed_data is None:
                raise ValueError("seed_data (password/secret) is required for user_secret method")
            from seeds.user_secret import generate_user_secret_seed
            seed = generate_user_secret_seed(seed_data)
        else:
            raise ValueError(f"Unknown seed_method: {seed_method}")

        self.key_material = generate_key_family(
            master_seed=seed,
            role=self.role,
            use_cashaddr_for_bch=use_cashaddr
        )
        return {
            "wallet_id": self.wallet_id,
            "role": self.role,
            "role_name": self.role_info.get("name"),
            "btc_address": self.key_material["families"]["btc"]["standard"],
            "bch_address": self.key_material["families"]["bch"]["standard"],
        }

    def save(self, directory: str = "wallets", compatible: bool = False) -> Path:
        """
        Save wallet as .kchain file.
        If compatible=True, tries to match the structure used by your existing tools.
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"{self.wallet_id}.kchain"

        if compatible:
            # More compatible structure (closer to your real .kchain files)
            data = {
                "wallet_id": self.wallet_id,
                "created_at": self.created_at,
                "role": self.role,
                "keys": {
                    "sphincs128s_master_pk": self.key_material.get("sphinx_105_byte_master_hex", ""),
                    "role": self.role,
                    "btc": self.key_material["families"]["btc"] if self.key_material else {},
                    "bch": self.key_material["families"]["bch"] if self.key_material else {},
                }
            }
        else:
            data = {
                "wallet_id": self.wallet_id,
                "created_at": self.created_at,
                "role": self.role,
                "role_info": self.role_info,
                "key_material": self.key_material
            }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        self.path = path
        return path

    @classmethod
    def load(cls, path: str) -> "Wallet":
        with open(path, "r") as f:
            data = json.load(f)
        wallet = cls(wallet_id=data.get("wallet_id"))
        wallet.key_material = data.get("key_material") or data.get("keys")
        wallet.role = data.get("role", 5)
        return wallet

    def export(self, include_private: bool = False) -> Dict[str, Any]:
        export_data = {
            "wallet_id": self.wallet_id,
            "role": self.role,
            "addresses": {
                "btc": self.key_material["families"]["btc"]["standard"] if self.key_material else None,
                "bch": self.key_material["families"]["bch"]["standard"] if self.key_material else None,
            }
        }
        if include_private and self.key_material:
            export_data["key_material"] = self.key_material
        return export_data
