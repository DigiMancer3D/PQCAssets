# PQCassets

**Hybrid Post-Quantum Cryptography Asset Management System**

A practical toolkit for creating, protecting, and managing digital assets using a combination of classical and post-quantum cryptography. Built around a single master key that can derive multiple usable key families and a robust PQC-protected container format.

---

## Why

Most post-quantum cryptography standards today focus on replacing classical signatures with new algorithms (like Falcon and SPHINCS+). While important, this project takes a different approach:

- Explore **hybrid systems** that combine classical and post-quantum signatures.
- Use hash-2-hash processing for various actions.
- Build working tools using these hybrid signatures.

The goal is to make post-quantum protection **usable today** on normal computers, while preparing for a future where quantum computers become more accessible.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/DigiMancer3D/PQCAssets.git
cd PQCAssets

# 2. Run the full test suite (recommended first step)
python3 tests/run_full_test_suite.py
```

If all tests pass, you're ready to use the tools.

---

## Main Tool: PAH Bulk PQC Wrapper

The core practical tool is `pah/pah_wrap_improved.py`. It lets you:

- Wrap individual files or entire folders
- Create multi-asset containers (PQC-protected archives)
- List, extract, split, and verify containers
- Use Falcon, SPHINCS+, or Hybrid signatures

### Common Commands

```bash
# Create a protected container from a folder
python3 pah/pah_wrap_improved.py path/to/folder/ --container --name my_assets --algorithm hybrid

# List what's inside a container
python3 pah/pah_wrap_improved.py pqc_wrapped/my_assets.pqcasset --list

# Extract everything from a container
python3 pah/pah_wrap_improved.py pqc_wrapped/my_assets.pqcasset --extract-all --output-dir ./restored/

# Split a container into 4 parts (by count)
python3 pah/pah_wrap_improved.py pqc_wrapped/my_assets.pqcasset --split 4 --output-prefix part

# Split a container by approximate size (e.g. 5MB per part)
python3 pah/pah_wrap_improved.py pqc_wrapped/my_assets.pqcasset --split-size 5M --output-prefix chunk

# Verify a container is valid
python3 pah/pah_wrap_improved.py pqc_wrapped/my_assets.pqcasset --verify

# Extract only after verifying
python3 pah/pah_wrap_improved.py pqc_wrapped/my_assets.pqcasset --extract-all --verify --output-dir ./safe/

# Clean up messy double-wrapped files
python3 pah/pah_wrap_improved.py --clean-stacked
```

---

## Running Tests

The project includes a comprehensive test suite:

```bash
python3 tests/run_full_test_suite.py
```

This runs:
- Sphinx+ key generation
- Full PAH wrapper lifecycle (create, wrap, list, extract, split, verify, repack)
- Both count-based and size-based splitting with timing
- Role system checks
- End-to-end smoke tests

---

## Technical Overview

### Sphinx+ Master Key
Everything starts from one modified Sphinx+ key. From this single secret, the system can derive:

- Bitcoin (BTC) addresses
- Bitcoin Cash (BCH) addresses
- Full Sphinx+ keys
- Hybrid (classical + PQC) keys
- Self-Verifying Coin (SVC) identifiers

### PAH Container Format
The `pah_wrap_improved.py` tool creates `.pqcasset` files/containers that contain:

- Per-entry signatures (Falcon, SPHINCS+, or Hybrid)
- Original data
- Optional content hashes and manifests

Containers can be split, verified, and extracted.

### Hybrid Signatures
We combine classical signatures with post-quantum ones (Falcon + SPHINCS+) to get the best of both worlds: smaller sizes where possible and stronger long-term security.

---

**Sometimes all we can do is try & be creative. So, I did & I will.**


---
