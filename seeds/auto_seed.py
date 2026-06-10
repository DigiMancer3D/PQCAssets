#!/usr/bin/env python3
"""
seeds/auto_seed.py
Simple cryptographically secure auto-generated seed
"""

import secrets
from typing import Optional

def generate_auto_seed(length: int = 32) -> bytes:
    """Generate a secure random seed."""
    return secrets.token_bytes(length)
