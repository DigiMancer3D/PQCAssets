#!/usr/bin/env python3
"""
seeds/user_secret.py
User-Provided Secret → Strong Cryptographic Seed

This module implements logic similar to ring_password.c:
- Takes a user password/secret
- Hashes it with SHA3-512 (Ring0 style)
- Further strengthens it with SHAKE256
- Returns a high-quality seed suitable for wallet generation
"""

import hashlib
from typing import Union


def generate_user_secret_seed(secret: Union[str, bytes], output_len: int = 32) -> bytes:
    """
    Convert a user-provided secret/password into a strong seed.

    This follows the same philosophy as ring_password.c:
    - SHA3-512 is used as the base hash (matching your C code)
    - SHAKE256 is used for final expansion (consistent with other seed methods)

    The user never sees the final seed — only the original password they provided.
    """
    if isinstance(secret, str):
        secret = secret.encode("utf-8")

    # Step 1: SHA3-512 (same as ring_password.c)
    sha3_digest = hashlib.sha3_512(secret).digest()

    # Step 2: Strengthen with SHAKE256 (consistent with other methods in the project)
    final_seed = hashlib.shake_256(sha3_digest).digest(output_len)

    return final_seed
