#!/usr/bin/env python3
"""
economy/roles_integration.py
Phase 6-1 - Role System Integration Layer

This module provides a clean interface between the economy system
and your existing roles/role_system.py.

It defines clear functions that the economy modules can call.
You can later replace the default implementations with calls
to your real role system.

Default behavior uses simple integer roles (0 = highest privilege).
"""

from typing import Any, Optional, Protocol


class RoleChecker(Protocol):
    """Protocol that your real role system can implement."""
    def get_role(self, actor: Any) -> int: ...
    def can_mint(self, actor_role: int) -> bool: ...
    def can_burn(self, actor_role: int, asset_owner_role: int) -> bool: ...
    def can_transfer(self, actor_role: int, asset_owner_role: int) -> bool: ...
    def can_use_template(self, actor_role: int, template_allowed_roles: list) -> bool: ...


# ============================================================
# Default Simple Implementation (can be replaced)
# ============================================================

class DefaultRoleChecker:
    """
    Simple role checker using integer roles.
    Role 0 = highest privilege (admin/master)
    Lower number = more privileged
    """

    def get_role(self, actor: Any) -> int:
        if isinstance(actor, int):
            return actor
        if hasattr(actor, "role"):
            return getattr(actor, "role")
        return 5  # Default to normal player role

    def can_mint(self, actor_role: int) -> bool:
        return actor_role <= 0  # Only admins can mint by default

    def can_burn(self, actor_role: int, asset_owner_role: int) -> bool:
        return actor_role <= asset_owner_role

    def can_transfer(self, actor_role: int, asset_owner_role: int) -> bool:
        return actor_role <= asset_owner_role

    def can_use_template(self, actor_role: int, template_allowed_roles: list) -> bool:
        return actor_role in template_allowed_roles or actor_role <= 0


# Global instance that economy modules will use
_role_checker: RoleChecker = DefaultRoleChecker()


def set_role_checker(checker: RoleChecker):
    """Replace the default role checker with your real implementation."""
    global _role_checker
    _role_checker = checker


def get_role(actor: Any) -> int:
    return _role_checker.get_role(actor)


def can_mint(actor: Any) -> bool:
    role = get_role(actor)
    return _role_checker.can_mint(role)


def can_burn(actor: Any, asset_owner_role: int) -> bool:
    role = get_role(actor)
    return _role_checker.can_burn(role, asset_owner_role)


def can_transfer(actor: Any, asset_owner_role: int) -> bool:
    role = get_role(actor)
    return _role_checker.can_transfer(role, asset_owner_role)


def can_use_template(actor: Any, template_allowed_roles: list) -> bool:
    role = get_role(actor)
    return _role_checker.can_use_template(role, template_allowed_roles)


# ============================================================
# Future: Secret Percentage / Pattern Recognition Hook
# ============================================================

def check_secret_percentage(data: Any) -> float:
    """
    Placeholder for your advanced logic that calculates
    how many secrets were visible when data is decoupled.

    This was mentioned in your original design for role allowance.
    """
    # TODO: Implement real logic from your role_system
    return 0.0
