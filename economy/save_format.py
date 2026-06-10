#!/usr/bin/env python3
"""
economy/save_format.py
Phase 5.3 - PQC-Safe Game Save Format (with real PAH signing)

This module now supports real PQC signing using the PAH tool
(Falcon / SPHINCS+ / Hybrid) so game saves are cryptographically protected.
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime, timezone


def _find_pah_binary() -> Optional[str]:
    """Reuse robust finder logic"""
    candidates = [
        os.path.expanduser("~/new_thing/pah/pah"),
        os.path.join(os.getcwd(), "..", "pah", "pah"),
        os.path.join(os.getcwd(), "pah", "pah"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


@dataclass
class GameSave:
    player_id: str
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    economy_state: Dict[str, Any] = field(default_factory=dict)
    player_state: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None          # Will store path to .pqcasset or signature info
    pah_signed_path: Optional[str] = None    # Path to the actual PQC-signed save file

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "version": self.version,
            "created_at": self.created_at,
            "economy_state": self.economy_state,
            "player_state": self.player_state,
            "signature": self.signature,
            "pah_signed_path": self.pah_signed_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameSave":
        return cls(
            player_id=data["player_id"],
            version=data.get("version", 1),
            created_at=data.get("created_at", ""),
            economy_state=data.get("economy_state", {}),
            player_state=data.get("player_state", {}),
            signature=data.get("signature"),
            pah_signed_path=data.get("pah_signed_path"),
        )

    def sign_with_pah(self, algorithm: str = "falcon") -> Optional[str]:
        """
        Signs the save using the PAH tool (real PQC signature).
        Returns the path to the .pqcasset signed file, or None on failure.
        """
        pah_binary = _find_pah_binary()
        if not pah_binary:
            print("[GameSave] ERROR: Could not find pah binary for signing.")
            return None

        # Serialize current state to a temp JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(self.to_dict(), tmp, indent=2)
            temp_json_path = tmp.name

        output_path = temp_json_path + ".pqcasset"

        cmd = [pah_binary, f"--wrap-{algorithm}", temp_json_path, output_path]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.pah_signed_path = output_path
                self.signature = f"PAH_{algorithm.upper()}_SIGNED:{output_path}"
                print(f"[GameSave] Successfully PQC-signed save → {output_path}")
                return output_path
            else:
                print(f"[GameSave] PAH signing failed:\n{result.stderr}")
                return None
        except Exception as e:
            print(f"[GameSave] Error during PAH signing: {e}")
            return None
        finally:
            # Clean up temp JSON
            if os.path.exists(temp_json_path):
                os.unlink(temp_json_path)

    def verify_with_pah(self) -> bool:
        """
        Verifies the PQC signature using PAH.
        """
        if not self.pah_signed_path or not os.path.exists(self.pah_signed_path):
            return False

        pah_binary = _find_pah_binary()
        if not pah_binary:
            return False

        cmd = [pah_binary, "--verify", self.pah_signed_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception:
            return False
