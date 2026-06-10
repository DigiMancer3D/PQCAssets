#!/usr/bin/env python3
from wallet.wallet import Wallet

w = Wallet()
info = w.create(seed_method="auto")
print("Wallet created:", info["wallet_id"])
print("Role:", info["role"])

path = w.save(compatible=True)
print("Saved compatible .kchain to:", path)
print("\n✅ Test passed!")
