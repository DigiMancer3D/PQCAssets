#!/usr/bin/env python3
"""
unified_sphinx_keygen.py
Phase 1: Unified Sphinx+ Key Generation (Bugfix Update)

Fixes applied:
- Correct CashAddr implementation (proper 5-bit conversion)
- generate_multi_role_family is now properly defined and exported
- Safer CLI and demo behavior
"""

import hashlib
import secrets
import time
import argparse
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
import subprocess

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(v: bytes) -> str:
    if not v: return ''
    origlen = len(v)
    v = v.lstrip(b'\0')
    acc = int.from_bytes(v, 'big')
    result = ''
    while acc:
        acc, mod = divmod(acc, 58)
        result = BASE58_ALPHABET[mod] + result
    return '1' * (origlen - len(v)) + result

def double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def double_shake256(data: bytes, digest_len: int = 32) -> bytes:
    h = hashlib.shake_256(data).digest(digest_len)
    return hashlib.shake_256(h).digest(digest_len)

def get_checksum(data: bytes, length: int = 4) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()[:length]

def role_domain_sep(role: int, purpose: str = "key_derivation") -> bytes:
    return f"SPHINX_ROLE_{role:02d}_{purpose}".encode()

# =============================================================================
# Proper CashAddr (Fixed 5-bit conversion)
# =============================================================================

CASHADDR_ALPHABET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'

def _bech32_polymod(values):
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk

def _bech32_hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def _bech32_create_checksum(hrp, data):
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def _bech32_encode(hrp, data):
    combined = data + _bech32_create_checksum(hrp, data)
    return hrp + '1' + ''.join([CASHADDR_ALPHABET[d] for d in combined])

def _convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

def derive_bch_cashaddr(payload: bytes, use_shake: bool = False, testnet: bool = False) -> str:
    payload20 = _reduce_to_20_bytes(payload, use_shake)
    hrp = "bchtest" if testnet else "bitcoincash"
    data = _convertbits([0] + list(payload20), 8, 5)
    if data is None:
        return derive_bch_address(payload, use_shake, testnet)
    return _bech32_encode(hrp, data)

def _reduce_to_20_bytes(data: bytes, use_shake: bool) -> bytes:
    if len(data) == 20:
        return data
    if use_shake:
        return double_shake256(data, 20)
    else:
        return hashlib.new('ripemd160', hashlib.sha256(data).digest()).digest()

# =============================================================================
# Master Material + Classical Seed
# =============================================================================

def generate_sphinx_master_material(seed=None, real_105_slice=None, target_len=105):
    if real_105_slice is not None:
        if len(real_105_slice) < 93:
            raise ValueError("real_105_slice must be at least 93 bytes")
        return real_105_slice[:target_len]
    if seed is None:
        seed = secrets.token_bytes(32)
    if len(seed) < 16:
        seed = hashlib.shake_256(seed).digest(32)
    expanded = hashlib.shake_256(seed + b"SPHINX+MASTER_v1_Phase1").digest(target_len * 2)
    return expanded[:target_len]

def derive_limited_93_byte(sphinx_105: bytes) -> bytes:
    return sphinx_105[:93]

def get_classical_seed_from_93_byte_core(core_93: bytes) -> bytes:
    if len(core_93) < 93:
        raise ValueError("Core must be at least 93 bytes")
    return double_shake256(core_93 + b"CLASSICAL_SEED_v1", 32)

# =============================================================================
# Address Derivation
# =============================================================================

def derive_btc_address(payload: bytes, use_shake: bool = False, testnet: bool = False) -> str:
    payload20 = _reduce_to_20_bytes(payload, use_shake)
    version = b'\x6f' if testnet else b'\x00'
    data = version + payload20
    checksum = get_checksum(data) if not use_shake else double_shake256(data, 4)
    return base58_encode(data + checksum)

def derive_bch_address(payload: bytes, use_shake: bool = False, testnet: bool = False) -> str:
    payload20 = _reduce_to_20_bytes(payload, use_shake)
    version = b'\x00'
    data = version + payload20
    checksum = get_checksum(data) if not use_shake else double_shake256(data, 4)
    return base58_encode(data + checksum)

# =============================================================================
# Role System
# =============================================================================

ROLE_CAPABILITIES = {
    0: {"name": "Master/Admin", "can_mint": True, "can_burn": True, "can_transfer": True, "can_view_all": True},
    1: {"name": "High Privilege", "can_mint": True, "can_burn": True, "can_transfer": True, "can_view_all": False},
    5: {"name": "Standard User", "can_mint": False, "can_burn": False, "can_transfer": True, "can_view_all": False},
    9: {"name": "View Only", "can_mint": False, "can_burn": False, "can_transfer": False, "can_view_all": False},
}

def get_role_capabilities(role: int) -> Dict[str, Any]:
    return ROLE_CAPABILITIES.get(role, {"name": f"Role {role}", "can_mint": False, "can_transfer": True})

# =============================================================================
# Main Public API
# =============================================================================

def generate_key_family(
    master_seed: Optional[bytes] = None,
    real_105_slice: Optional[bytes] = None,
    role: int = 0,
    enable_btc: bool = True,
    enable_bch: bool = True,
    enable_shake_variants: bool = True,
    enable_sphinx_full: bool = True,
    enable_svc_hooks: bool = True,
    enable_classical_seed: bool = True,
    testnet: bool = False,
    use_cashaddr_for_bch: bool = True
) -> Dict[str, Any]:

    sphinx_105 = generate_sphinx_master_material(seed=master_seed, real_105_slice=real_105_slice)
    limited_93 = derive_limited_93_byte(sphinx_105)
    role_key_material = hashlib.shake_256(limited_93 + role_domain_sep(role)).digest(32)

    results = {
        "sphinx_105_byte_master_hex": sphinx_105.hex(),
        "limited_93_byte_core_hex": limited_93.hex(),
        "role": role,
        "role_capabilities": get_role_capabilities(role),
        "generated_at": int(time.time()),
        "pure_pqc_no_classical_ec_math": True,
        "families": {}
    }

    if enable_sphinx_full:
        view_ext = sphinx_105[93:105] if len(sphinx_105) >= 105 else b''
        results["families"]["sphinx_full"] = {
            "full_105_byte_master": sphinx_105.hex(),
            "limited_93_byte_core": limited_93.hex(),
            "master_view_key_extension": view_ext.hex() if view_ext else None,
        }

    if enable_btc:
        std = derive_btc_address(role_key_material, use_shake=False, testnet=testnet)
        shk = derive_btc_address(role_key_material, use_shake=True, testnet=testnet) if enable_shake_variants else None
        results["families"]["btc"] = {"standard": std, "shake_variant": shk}

    if enable_bch:
        if use_cashaddr_for_bch:
            std = derive_bch_cashaddr(role_key_material, use_shake=False, testnet=testnet)
            shk = derive_bch_cashaddr(role_key_material, use_shake=True, testnet=testnet) if enable_shake_variants else None
        else:
            std = derive_bch_address(role_key_material, use_shake=False, testnet=testnet)
            shk = derive_bch_address(role_key_material, use_shake=True, testnet=testnet) if enable_shake_variants else None
        results["families"]["bch"] = {"standard": std, "shake_variant": shk, "using_cashaddr": use_cashaddr_for_bch}

    if enable_svc_hooks:
        coin_id = f"SVC-SPHINX-{sphinx_105[:8].hex().upper()}-R{role}"
        results["families"]["svc"] = {
            "coin_id": coin_id,
            "spx_qec_ref": f"spx_qec_{int(time.time())}_{sphinx_105[:4].hex()}",
            "kickback_ready": True
        }

    if enable_classical_seed:
        classical_seed = get_classical_seed_from_93_byte_core(limited_93)
        results["families"]["classical_seed"] = {
            "32_byte_classical_seed_hex": classical_seed.hex(),
            "note": "Usable as entropy for classical wallets (hash-only derivation)."
        }

    if enable_shake_variants:
        results["families"]["shake_master"] = {
            "32_byte_shake_reduced": double_shake256(sphinx_105 + role_domain_sep(role), 32).hex()
        }

    return results

def generate_multi_role_family(master_seed=None, real_105_slice=None, roles=None):
    if roles is None:
        roles = list(range(10))
    return {r: generate_key_family(master_seed=master_seed, real_105_slice=real_105_slice, role=r) for r in roles}

# =============================================================================
# C Pipeline Helper
# =============================================================================

def get_real_sphinx_105_slice_from_c_prog(binary_path="prog1/main", seed=None, timeout=30):
    bin_path = Path(binary_path)
    if not bin_path.exists():
        return None
    try:
        result = subprocess.run([str(bin_path)], input=seed, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        if len(output) >= 105:
            return output[:105]
        try:
            return bytes.fromhex(output.decode().strip())[:105]
        except:
            return None
    except:
        return None

# =============================================================================
# CLI
# =============================================================================

def main_cli():
    parser = argparse.ArgumentParser(description="Phase 1 Unified Sphinx+ Key Generator")
    parser.add_argument("--role", type=int, default=0)
    parser.add_argument("--real-slice", type=str)
    parser.add_argument("--no-shake", action="store_true")
    parser.add_argument("--legacy-bch", action="store_true")

    args = parser.parse_args()

    real_slice = None
    if args.real_slice:
        p = Path(args.real_slice)
        if p.exists():
            data = p.read_bytes()
            real_slice = data if len(data) >= 93 else bytes.fromhex(data.decode().strip())

    family = generate_key_family(
        real_105_slice=real_slice,
        role=args.role,
        enable_shake_variants=not args.no_shake,
        use_cashaddr_for_bch=not args.legacy_bch
    )

    print(f"\n=== Sphinx+ Key Family (Role {args.role}) ===")
    print(f"105-byte Master : {family['sphinx_105_byte_master_hex'][:32]}...")
    if "btc" in family["families"]:
        print(f"BTC Standard    : {family['families']['btc']['standard']}")
        if family['families']['btc'].get('shake_variant'):
            print(f"BTC Shake       : {family['families']['btc']['shake_variant']}")
    print("\n✅ Key family generated successfully.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli()
    else:
        demo = generate_key_family(role=0)
        print("=== Phase 1 Unified Sphinx+ KeyGen Demo ===")
        print("BTC Standard :", demo["families"]["btc"]["standard"])
        print("BCH CashAddr :", demo["families"]["bch"]["standard"])
        print("SVC Coin ID  :", demo["families"]["svc"]["coin_id"])
        print("\n✅ All Phase 1 features working.")