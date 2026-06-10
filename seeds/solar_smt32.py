#!/usr/bin/env python3
"""
seeds/solar_smt32.py
Solar SMT32 Microcontroller Seed Path - Full Implementation

Handles your exact data format:
- JSON, comma-separated, or colon-separated input
- Keys: h, d, x, y, z, i, e, checksum
- Applies z = (i * d) + z
- Recalculates checksum when missing or invalid
- Performs intensity folding + symmetry
- Converts to binary → trinary PQC seed with data hiding
"""

import json
import hashlib
from typing import Dict, Any, Union


def _recalculate_checksum(data: Dict[str, Any]) -> str:
    """Calculate checksum = shake256(sha256 of stacked values without keys)."""
    stacked = "".join(str(data.get(k, "")) for k in ['h', 'd', 'x', 'y', 'z', 'i', 'e'])
    sha = hashlib.sha256(stacked.encode()).digest()
    return hashlib.shake_256(sha).hexdigest(16)


def parse_solar_input(data: Union[str, dict, bytes]) -> Dict[str, Any]:
    """
    Parse SMT32 data from multiple formats.
    Returns normalized dict with keys: h, d, x, y, z, i, e, checksum
    """
    if isinstance(data, dict):
        parsed = data
    else:
        text = data.decode(errors='ignore').strip() if isinstance(data, (bytes, bytearray)) else str(data).strip()
        text = text.strip('{}')

        if text.startswith('{'):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = {}
        else:
            # Delimited (comma or colon)
            if ',' in text:
                parts = [p.strip() for p in text.split(',')]
            else:
                parts = [p.strip() for p in text.split(':')]

            keys = ['h', 'd', 'x', 'y', 'z', 'i', 'e', 'checksum']
            parsed = {}
            for i, key in enumerate(keys):
                if i < len(parts):
                    val = parts[i]
                    parsed[key] = int(val) if str(val).isdigit() else val

    # Normalize keys to single letters
    result = {}
    key_map = {
        'h': 'h', 'hits': 'h',
        'd': 'd', 'duration': 'd',
        'x': 'x', 'y': 'y', 'z': 'z',
        'i': 'i', 'intensity': 'i',
        'e': 'e', 'epoch': 'e',
        'checksum': 'checksum'
    }

    for k, v in parsed.items():
        lk = str(k).lower()
        if lk in key_map:
            result[key_map[lk]] = v

    # Ensure all required keys exist
    for key in ['h', 'd', 'x', 'y', 'z', 'i', 'e']:
        if key not in result:
            result[key] = 0

    # Apply formula: z = (i * d) + z
    try:
        result['z'] = (int(result.get('i', 0)) * int(result.get('d', 0))) + int(result.get('z', 0))
    except (ValueError, TypeError):
        pass

    # Checksum validation + recalculation
    provided = str(result.get('checksum', '')).strip()
    recalculated = _recalculate_checksum(result)
    result['checksum_recalculated'] = bool(not provided or provided != recalculated)
    if result['checksum_recalculated']:
        result['checksum'] = recalculated

    return result


def fold_intensity(x: int, y: int, intensity: int, duration: int) -> tuple:
    """Apply symmetry folding (up/down + left/right)."""
    fx = (x + y) // 2
    fy = abs(x - y)
    color_intensity = min(255, int((intensity * duration) / 1000))
    return fx, fy, color_intensity


def generate_solar_trinary_seed(data: Union[str, dict, bytes], output_len: int = 32) -> bytes:
    """Main function: Convert SMT32 data into trinary PQC seed."""
    parsed = parse_solar_input(data)

    h = int(parsed.get('h', 0))
    d = int(parsed.get('d', 0))
    x = int(parsed.get('x', 0))
    y = int(parsed.get('y', 0))
    z = int(parsed.get('z', 0))
    i = int(parsed.get('i', 0))
    e = int(parsed.get('e', 0))

    # Intensity folding
    fx, fy, color_intensity = fold_intensity(x, y, i, d)

    # Build binary representation
    binary_str = ""
    for val in [h, d, fx, fy, z, color_intensity, e]:
        binary_str += format(val, 'b')

    # Binary → Trinary with data hiding/rolling
    trinary = ""
    for idx, bit in enumerate(binary_str):
        if idx % 3 == 0:
            trinary += '0' if bit == '0' else '1'
        elif idx % 3 == 1:
            trinary += '1' if bit == '0' else '2'
        else:
            trinary += '2' if bit == '0' else '0'

    seed_input = trinary.encode() + str(e).encode()
    return hashlib.shake_256(seed_input).digest(output_len)


def process_solar_smt32_data(data: Union[str, dict, bytes]) -> Dict[str, Any]:
    """Full processing pipeline + generated seed."""
    parsed = parse_solar_input(data)
    seed = generate_solar_trinary_seed(parsed)
    parsed['generated_seed_hex'] = seed.hex()
    return parsed
