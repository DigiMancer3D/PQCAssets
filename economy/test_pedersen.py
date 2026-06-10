#!/usr/bin/env python3
"""Quick test for Phase 5.1 Pedersen module"""

from economy.pedersen import generate_pedersen_params, PedersenCommitment
import os

def main():
    params = generate_pedersen_params()

    blinding1 = os.urandom(32)
    blinding2 = os.urandom(32)

    c1 = PedersenCommitment.commit(params, value=100, blinding=blinding1)
    c2 = PedersenCommitment.commit(params, value=50, blinding=blinding2)

    total = c1 + c2
    diff = c1 - c2

    print("Commitment 1:", c1)
    print("Commitment 2:", c2)
    print("Total (c1 + c2):", total)
    print("Diff (c1 - c2):", diff)

    # Verify
    combined_blinding = (int.from_bytes(blinding1, "big") + int.from_bytes(blinding2, "big")) % params.curve.group_order
    combined_blinding_bytes = combined_blinding.to_bytes(32, "big")

    print("\nDoes total open to 150?", total.verify(150, combined_blinding_bytes))
    print("Does diff open to 50?", diff.verify(50, blinding1))  # simplistic check

if __name__ == "__main__":
    main()
