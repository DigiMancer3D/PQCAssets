#!/usr/bin/env python3
"""
economy/templates.py
Phase 5.4 - Confidential Transaction Templates + Counter-Templates

This module introduces a template system for economy actions.
Templates define how assets/coins can be moved or transformed
while supporting confidential amounts (via Pedersen) and PQC signatures.

Features:
- TransactionTemplate: defines a signed, confidential transaction pattern
- Support for counter-templates (can cancel or reverse another template)
- Role-based template usage permissions
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .pedersen import PedersenParams, PedersenCommitment
from .asset import PQCAsset
from .roles_integration import can_use_template, get_role


@dataclass
class TransactionTemplate:
    """
    A reusable template for confidential economy transactions.
    Can be published by players/admins and used (or countered) by others.
    """
    template_id: str
    creator_role: int
    description: str
    action_type: str                    # e.g. "transfer", "mint", "burn", "trade"
    requires_amount: bool = True
    confidential: bool = True           # Whether amounts are hidden via Pedersen
    allowed_roles: List[int] = field(default_factory=lambda: [0, 5])  # Who can use this template
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: Optional[str] = None     # PQC signature of the template itself

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "creator_role": self.creator_role,
            "description": self.description,
            "action_type": self.action_type,
            "requires_amount": self.requires_amount,
            "confidential": self.confidential,
            "allowed_roles": self.allowed_roles,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransactionTemplate":
        return cls(**data)

    def can_be_used_by(self, actor: Any) -> bool:
        return can_use_template(actor, self.allowed_roles)

    def sign(self, private_key_material: bytes):
        """Placeholder for PQC signing of the template definition"""
        self.signature = "PQC_TEMPLATE_SIG_" + private_key_material.hex()[:16]


@dataclass
class CounterTemplate:
    """
    A template that can cancel or reverse the effect of another template.
    Useful for dispute resolution or role-controlled reversals.
    """
    counter_id: str
    targets_template_id: str
    creator_role: int
    reason: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counter_id": self.counter_id,
            "targets_template_id": self.targets_template_id,
            "creator_role": self.creator_role,
            "reason": self.reason,
            "created_at": self.created_at,
        }


class TemplateRegistry:
    """
    Central registry for published transaction templates and their counters.
    """

    def __init__(self):
        self.templates: Dict[str, TransactionTemplate] = {}
        self.counters: Dict[str, List[CounterTemplate]] = {}

    def publish_template(self, template: TransactionTemplate) -> bool:
        if template.template_id in self.templates:
            return False
        self.templates[template.template_id] = template
        print(f"[TemplateRegistry] Published template: {template.template_id}")
        return True

    def publish_counter(self, counter: CounterTemplate) -> bool:
        if counter.targets_template_id not in self.templates:
            return False
        if counter.targets_template_id not in self.counters:
            self.counters[counter.targets_template_id] = []
        self.counters[counter.targets_template_id].append(counter)
        print(f"[TemplateRegistry] Published counter for template {counter.targets_template_id}")
        return True

    def get_active_templates(self, actor: Any) -> List[TransactionTemplate]:
        return [t for t in self.templates.values() if t.can_be_used_by(actor)]

    def get_counters_for(self, template_id: str) -> List[CounterTemplate]:
        return self.counters.get(template_id, [])

    def save(self, filepath: str):
        data = {
            "templates": {tid: t.to_dict() for tid, t in self.templates.items()},
            "counters": {tid: [c.to_dict() for c in clist] for tid, clist in self.counters.items()},
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[TemplateRegistry] Saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "TemplateRegistry":
        registry = cls()
        if not os.path.exists(filepath):
            return registry
        with open(filepath, "r") as f:
            data = json.load(f)
        for tid, tdata in data.get("templates", {}).items():
            registry.templates[tid] = TransactionTemplate.from_dict(tdata)
        for tid, clist in data.get("counters", {}).items():
            registry.counters[tid] = [CounterTemplate(**cdata) for cdata in clist]
        return registry
