#!/usr/bin/env python3
"""
seeds/trinary_dowsing.py
Trinary / high-density “fake dowsing” sampling
"""

import hashlib
import secrets
from typing import Optional

def generate_trinary_dowsing_seed(entropy: Optional[bytes] = None, output_len: int = 32) -> bytes:
    """
    High-density trinary-style seed using repeated hashing + folding.
    """
    if entropy is None:
        entropy = secrets.token_bytes(32)

    seed = entropy
    for i in range(4):
        seed = hashlib.shake_256(seed + i.to_bytes(1, 'big')).digest(64)
        seed = bytes(a ^ b for a, b in zip(seed[:32], seed[32:]))

    return hashlib.shake_256(seed).digest(output_len)
