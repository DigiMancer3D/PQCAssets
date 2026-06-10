#!/usr/bin/env python3
"""
chain_data_loader.py v1.1 - Dynamic loader with Fernet decryption + BCH support

Improvements in v1.1:
- Automatic decryption support for Fernet-encrypted files (.enc) and data
- Better Bitcoin Cash (BCH) detection: CashAddr, OP_RETURN, common BCH patterns
"""

import re
import json
import os
import base64
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any, Tuple

# Optional: cryptography for Fernet decryption
try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

# Try to import FusionHash
try:
    from fusion_hash import FusionHash, create_fusion
    HAS_FUSION_HASH = True
except ImportError:
    HAS_FUSION_HASH = False


# =============================================================================
# ParsedChainData
# =============================================================================

@dataclass
class ParsedChainData:
    """
    Structured container for parsed blockchain data.

    New in this version:
    - utxo_amounts: List of (utxo, amount) pairs when they can be associated.
      This is more robust than parallel lists.
    """
    txids: List[str] = field(default_factory=list)
    utxos: List[str] = field(default_factory=list)
    block_hashes: List[str] = field(default_factory=list)
    taproot_commitments: List[str] = field(default_factory=list)
    raw_texts: List[str] = field(default_factory=list)
    amounts: List[int] = field(default_factory=list)

    # New: Paired UTXO + amount data (preferred when available)
    utxo_amounts: List[Tuple[str, Optional[int]]] = field(default_factory=list)

    def get_utxos(self) -> List[str]:
        return self.utxos

    def get_txids(self) -> List[str]:
        return self.txids

    def get_utxo_amount_pairs(self) -> List[Tuple[str, Optional[int]]]:
        """Returns paired (utxo, amount) data when available."""
        return self.utxo_amounts

    def add_utxo_amount_pair(self, utxo: str, amount: Optional[int] = None):
        """Manually add a paired UTXO + amount (useful for post-processing)."""
        if utxo not in [u for u, _ in self.utxo_amounts]:
            self.utxo_amounts.append((utxo, amount))

    def get_block_hashes(self) -> List[str]:
        return self.block_hashes

    def get_taproot_commitments(self) -> List[str]:
        return self.taproot_commitments

    def has_data(self) -> bool:
        return bool(self.txids or self.utxos or self.block_hashes or
                    self.taproot_commitments or self.raw_texts)

    def to_fusion_hashes(self, bit_length: Optional[int] = None) -> List['FusionHash']:
        """
        Convert parsed data into FusionHash objects.

        When paired UTXO + amount data is available (utxo_amounts),
        this method creates **exactly one FusionHash per UTXO**.
        This is the recommended and cleanest behavior.
        """
        if not HAS_FUSION_HASH:
            raise ImportError("fusion_hash module not available.")

        results = []

        # Dynamic bit length
        effective_bit_length = bit_length
        if effective_bit_length is None and self.amounts:
            max_amt = max(self.amounts) if self.amounts else 0
            effective_bit_length = max_amt.bit_length() + 16

        # === Primary path: One FusionHash per paired UTXO ===
        if self.utxo_amounts:
            for utxo, amt in self.utxo_amounts:
                amount = amt if amt is not None else 0
                try:
                    fh = create_fusion([amount], bit_length=effective_bit_length)
                    results.append(fh)
                except Exception as e:
                    print(f"Warning: Could not create FusionHash for {utxo}: {e}")

        # Fallback paths
        elif self.utxos and self.amounts:
            n = max(len(self.utxos), len(self.amounts))
            for i in range(n):
                amt = self.amounts[i] if i < len(self.amounts) else 0
                try:
                    fh = create_fusion([amt], bit_length=effective_bit_length)
                    results.append(fh)
                except Exception as e:
                    print(f"Warning: Could not create FusionHash: {e}")

        elif self.amounts:
            for amt in self.amounts:
                try:
                    fh = create_fusion([amt], bit_length=effective_bit_length)
                    results.append(fh)
                except Exception as e:
                    print(f"Warning: Could not create FusionHash for amount {amt}: {e}")

        else:
            # Placeholders from any identifiers
            identifiers = self.txids + self.utxos + self.taproot_commitments + self.block_hashes
            for _ in identifiers:
                try:
                    fh = create_fusion([0], bit_length=effective_bit_length or 64)
                    results.append(fh)
                except Exception as e:
                    print(f"Warning: Could not create placeholder FusionHash: {e}")

        return results

    def summary(self) -> str:
        return (f"ParsedChainData("
                f"txids={len(self.txids)}, "
                f"utxos={len(self.utxos)}, "
                f"paired_utxo_amounts={len(self.utxo_amounts)}, "
                f"block_hashes={len(self.block_hashes)}, "
                f"taproot={len(self.taproot_commitments)}, "
                f"amounts={len(self.amounts)})")


# =============================================================================
# DataLoader with decryption + BCH support
# =============================================================================

class DataLoader:
    # Enhanced patterns
    TXID_PATTERN = re.compile(r'\b([0-9a-fA-F]{64})\b')
    UTXO_PATTERN = re.compile(r'\b([0-9a-fA-F]{64}):(\d+)\b')
    CASHADDR_PATTERN = re.compile(
        r'\b(bitcoincash|bchtest|bchreg):([qp][a-z0-9]{41,})\b', re.IGNORECASE
    )
    TAPROOT_PATTERN = re.compile(
        r'(taproot|tapleaf|commitment)[:=\s]*["\']?([0-9a-fA-F]{64,66})["\']?', re.IGNORECASE
    )
    OP_RETURN_PATTERN = re.compile(r'OP_RETURN|6a[0-9a-fA-F]{2,}', re.IGNORECASE)

    def __init__(self, fernet_key: Optional[bytes] = None):
        self.data = ParsedChainData()
        self.fernet_key = fernet_key

    def set_fernet_key(self, key: bytes):
        """Set the decryption key for Fernet-encrypted files."""
        self.fernet_key = key

    def load_from_file(self, path: str) -> ParsedChainData:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, 'rb') as f:
            raw = f.read()

        # Try decryption if it looks encrypted
        if path.endswith('.enc') or raw.startswith(b'gAAAAAB'):
            decrypted = self._try_decrypt(raw)
            if decrypted:
                content = decrypted.decode('utf-8', errors='ignore')
                return self._parse_content(content, source=path)
            else:
                print("⚠️  Could not decrypt file. Continuing with raw content...")

        # Normal text/JSON parsing
        try:
            content = raw.decode('utf-8', errors='ignore')
        except:
            content = str(raw)

        return self._parse_content(content, source=path)

    def load_from_string(self, text: str) -> ParsedChainData:
        return self._parse_content(text, source="terminal")

    def _try_decrypt(self, data: bytes) -> Optional[bytes]:
        if not HAS_CRYPTOGRAPHY:
            print("⚠️  'cryptography' package not installed. Cannot decrypt Fernet files.")
            print("   Run: pip install cryptography")
            return None

        if self.fernet_key is None:
            print("⚠️  No Fernet key provided. Use loader.set_fernet_key(your_key) or pass it to DataLoader().")
            return None

        try:
            f = Fernet(self.fernet_key)
            return f.decrypt(data)
        except InvalidToken:
            print("⚠️  Invalid Fernet key or corrupted data.")
            return None
        except Exception as e:
            print(f"⚠️  Decryption error: {e}")
            return None

    def _parse_content(self, content: str, source: str = "") -> ParsedChainData:
        self.data = ParsedChainData()

        # Try JSON
        if self._looks_like_json(content):
            try:
                parsed = json.loads(content)
                self._extract_from_json(parsed)
                return self.data
            except json.JSONDecodeError:
                pass

        # Text parsing
        self._extract_with_regex(content)
        self._extract_with_labels(content)
        return self.data

    def _looks_like_json(self, text: str) -> bool:
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))

    def _extract_from_json(self, data: Any, parent_key: str = ""):
        if isinstance(data, dict):
            current_utxo = None
            current_amount = None

            for key, value in data.items():
                key_lower = key.lower()
                if isinstance(value, (str, int)):
                    val_str = str(value)

                    if any(x in key_lower for x in ['utxo', 'outpoint']):
                        m = self.UTXO_PATTERN.search(val_str)
                        if m:
                            current_utxo = f"{m.group(1)}:{m.group(2)}"

                    if any(x in key_lower for x in ['amount', 'value', 'sat']):
                        try:
                            current_amount = int(float(val_str))
                        except ValueError:
                            pass

                    self._process_value(key_lower, val_str)

                elif isinstance(value, (dict, list)):
                    self._extract_from_json(value, key_lower)

            if current_utxo:
                self.data.add_utxo_amount_pair(current_utxo, current_amount)

        elif isinstance(data, list):
            for item in data:
                self._extract_from_json(item, parent_key)

    def _process_value(self, key: str, value: str):
        # TXID
        if any(x in key for x in ['txid', 'transaction', 'tx']):
            if re.fullmatch(r'[0-9a-fA-F]{64}', value):
                self.data.txids.append(value)

        # UTXO
        if any(x in key for x in ['utxo', 'outpoint']):
            m = self.UTXO_PATTERN.search(value)
            if m:
                self.data.utxos.append(f"{m.group(1)}:{m.group(2)}")

        # Amount
        if any(x in key for x in ['amount', 'value', 'sat']):
            try:
                amt = int(float(value))
                if amt > 0:
                    self.data.amounts.append(amt)
            except ValueError:
                pass

        # Block hash
        if 'block' in key and re.fullmatch(r'[0-9a-fA-F]{64}', value):
            self.data.block_hashes.append(value)

        # Taproot
        if any(x in key for x in ['taproot', 'tapleaf', 'commitment']):
            if re.fullmatch(r'[0-9a-fA-F]{64,66}', value):
                self.data.taproot_commitments.append(value)

    def _extract_with_regex(self, text: str):
        # UTXOs
        for m in self.UTXO_PATTERN.finditer(text):
            utxo = f"{m.group(1)}:{m.group(2)}"
            if utxo not in self.data.utxos:
                self.data.utxos.append(utxo)

        # TXIDs / Block hashes
        for m in self.TXID_PATTERN.finditer(text):
            h = m.group(1)
            ctx = text[max(0, m.start()-40):m.start()].lower()
            if 'block' in ctx:
                if h not in self.data.block_hashes:
                    self.data.block_hashes.append(h)
            else:
                if h not in self.data.txids:
                    self.data.txids.append(h)

        # CashAddr (BCH)
        for m in self.CASHADDR_PATTERN.finditer(text):
            addr = f"{m.group(1)}:{m.group(2)}"
            self.data.raw_texts.append(addr)  # store as raw for now

        # Taproot
        for m in self.TAPROOT_PATTERN.finditer(text):
            commit = m.group(2)
            if commit not in self.data.taproot_commitments:
                self.data.taproot_commitments.append(commit)

        # OP_RETURN detection (mark as raw text with note)
        if self.OP_RETURN_PATTERN.search(text):
            self.data.raw_texts.append("OP_RETURN data detected")

    def _extract_with_labels(self, text: str):
        labels = [
            r'txid[:=\s]*', r'utxo[:=\s]*', r'commitment[:=\s]*',
            r'taproot[:=\s]*', r'tapleaf[:=\s]*', r'blockhash[:=\s]*',
            r'amount[:=\s]*', r'value[:=\s]*', r'op_return[:=\s]*'
        ]
        pattern = re.compile(r'(' + '|'.join(labels) + r')\s*["\']?([^"\'\s,}\]]+)["\']?', re.IGNORECASE)

        for m in pattern.finditer(text):
            label = m.group(1).lower().strip(':=').strip()
            value = m.group(2).strip()

            if re.fullmatch(r'[0-9a-fA-F]{64}', value):
                if 'txid' in label: self.data.txids.append(value)
                elif 'block' in label: self.data.block_hashes.append(value)
                elif any(x in label for x in ['commitment', 'taproot', 'tapleaf']):
                    self.data.taproot_commitments.append(value)

            elif re.fullmatch(r'[0-9a-fA-F]{64}:\d+', value):
                self.data.utxos.append(value)

            elif label in ['amount', 'value']:
                try:
                    amt = int(float(value))
                    if amt > 0: self.data.amounts.append(amt)
                except ValueError:
                    pass


# =============================================================================
# Convenience
# =============================================================================

def load_chain_data(source: Union[str, os.PathLike], fernet_key: Optional[bytes] = None) -> ParsedChainData:
    loader = DataLoader(fernet_key=fernet_key)
    if os.path.exists(str(source)):
        return loader.load_from_file(str(source))
    else:
        return loader.load_from_string(str(source))


if __name__ == "__main__":
    print("=== chain_data_loader.py v1.1 Demo ===\n")

    example = '''
    txid: "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"
    utxo: "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678:0"
    amount: 123456789
    taproot_commitment: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
    bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy0h2k2
    '''

    data = load_chain_data(example)
    print(data.summary())
    print("TXIDs:", data.get_txids()[:2])
    print("UTXOs:", data.get_utxos())
    print("Taproot:", data.get_taproot_commitments())