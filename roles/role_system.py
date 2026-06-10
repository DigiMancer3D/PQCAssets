#!/usr/bin/env python3
"""
roles/role_system.py
Phase 3 - Expanded Role System + Master View Key Logic

Key concept:
- 93-byte limited core = restricted view
- 105-byte master = full material
- Master View Key = last 12 bytes of the 105-byte master (the difference)
"""

from typing import Dict, Any, Optional
import hashlib


ROLE_DEFINITIONS = {
    0: {
        "name": "Master/Admin",
        "can_mint": True,
        "can_burn": True,
        "can_transfer": True,
        "can_view_all": True,
        "description": "Full control + Master View Key access"
    },
    1: {
        "name": "High Privilege",
        "can_mint": True,
        "can_burn": True,
        "can_transfer": True,
        "can_view_all": False,
        "description": "High operational access"
    },
    5: {
        "name": "Standard User",
        "can_mint": False,
        "can_burn": False,
        "can_transfer": True,
        "can_view_all": False,
        "description": "Normal user operations"
    },
    9: {
        "name": "View Only",
        "can_mint": False,
        "can_burn": False,
        "can_transfer": False,
        "can_view_all": False,
        "description": "Read-only access"
    },
}


class RoleSystem:
    def __init__(self):
        self.roles = ROLE_DEFINITIONS.copy()

    def get_role(self, role_id: int) -> Dict[str, Any]:
        return self.roles.get(role_id, self.roles[5])

    def assign_role(self, requested_role: Optional[int] = None) -> int:
        if requested_role is not None and requested_role in self.roles:
            return requested_role
        return 5  # Default to Standard User

    def get_master_view_key(self, sphinx_105_hex: str) -> str:
        """
        Returns the Master View Key.
        This is the last 12 bytes (24 hex characters) of the 105-byte master.
        This is the key difference between the 93-byte limited core and the full 105-byte master.
        """
        if len(sphinx_105_hex) < 210:  # 105 bytes = 210 hex chars
            return ""
        return sphinx_105_hex[-24:]

    def derive_limited_93_from_105(self, sphinx_105_hex: str) -> str:
        """Returns only the limited 93-byte core from a full 105-byte master."""
        if len(sphinx_105_hex) < 186:
            return sphinx_105_hex
        return sphinx_105_hex[:186]


# Singleton
_role_system = RoleSystem()


def get_role_capabilities(role_id: int) -> Dict[str, Any]:
    return _role_system.get_role(role_id)


def assign_role(requested_role: Optional[int] = None) -> int:
    return _role_system.assign_role(requested_role)


def get_master_view_key(sphinx_105_hex: str) -> str:
    """Convenience function to get the Master View Key."""
    return _role_system.get_master_view_key(sphinx_105_hex)
