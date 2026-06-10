#!/usr/bin/env python3
"""
economy/pedersen.py
Simplified + Robust Pedersen Commitment Module (Phase 5/6)
"""

import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.backends import default_backend


def _get_curve_order(curve):
    if hasattr(curve, "group_order"):
        return curve.group_order
    return (1 << 256) - (1 << 224) + (1 << 192) + (1 << 96) - 1


@dataclass
class PedersenParams:
    curve: ec.EllipticCurve = ec.SECP256K1()
    G: ec.EllipticCurvePublicKey = None
    H: ec.EllipticCurvePublicKey = None

    def __post_init__(self):
        if self.G is None:
            priv = ec.derive_private_key(1, self.curve, default_backend())
            self.G = priv.public_key()

        if self.H is None:
            h_seed = b"GRILLS_Pedersen_H_v1_SVC"
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            digest.update(h_seed)
            h_bytes = digest.finalize()
            h_int = int.from_bytes(h_bytes, "big") % _get_curve_order(self.curve)
            priv = ec.derive_private_key(h_int, self.curve, default_backend())
            self.H = priv.public_key()


class PedersenCommitment:
    def __init__(self, params: PedersenParams, commitment_point: ec.EllipticCurvePublicKey):
        self.params = params
        self.C = commitment_point

    @classmethod
    def commit(cls, params: PedersenParams, value: int, blinding: Optional[bytes] = None):
        if blinding is None:
            blinding = os.urandom(32)

        curve_order = _get_curve_order(params.curve)
        value_int = value % curve_order
        blinding_int = int.from_bytes(blinding, "big") % curve_order

        value_point = ec.derive_private_key(value_int, params.curve, default_backend()).public_key()
        blinding_point = ec.derive_private_key(blinding_int, params.curve, default_backend()).public_key()

        combined_scalar = (value_int + blinding_int) % curve_order
        commitment_point = ec.derive_private_key(combined_scalar, params.curve, default_backend()).public_key()

        return cls(params, commitment_point)

    def verify(self, value: int, blinding: bytes) -> bool:
        curve_order = _get_curve_order(self.params.curve)
        value_int = value % curve_order
        blinding_int = int.from_bytes(blinding, "big") % curve_order
        expected = PedersenCommitment.commit(self.params, value, blinding)
        return self.C.public_numbers() == expected.C.public_numbers()

    def to_bytes(self) -> bytes:
        return self.C.public_bytes(Encoding.X962, PublicFormat.CompressedPoint)

    @classmethod
    def from_bytes(cls, params: PedersenParams, data: bytes):
        pubkey = ec.EllipticCurvePublicKey.from_encoded_point(params.curve, data)
        return cls(params, pubkey)

    def __repr__(self):
        return f"PedersenCommitment(C={self.to_bytes().hex()[:16]}...)"


def generate_pedersen_params() -> PedersenParams:
    return PedersenParams()
