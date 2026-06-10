# PQCAssets

**Post-Quantum Cryptography for real assets, games, and systems: built to work on ordinary computers today.**

PQCAssets is a practical toolkit that lets you protect files, game assets, and digital value using post-quantum cryptography (PQC) that runs on normal binary machines right now. It combines modified SPHINCS+ and FALCON signatures with hybrid methods, small output sizes. Using realistic test python game & assets as proof of concept demo.

---

## Why This Exists

Most people assume post-quantum cryptography is something that only becomes useful after quantum computers arrive. The reality is more interesting and more urgent.

NIST standardized a few post-quantum algorithms a couple of years ago. While those standards are important, they also contain known limitations and trade-offs. Instead of waiting for perfect quantum-resistant tools, this project explores how we can **use the current tools creatively** to get stronger protection today.

The core idea is simple:

> We don’t need a perfect quantum computer to start protecting things better. We can take existing post-quantum primitives (especially SPHINCS+ and FALCON), reshape how we use them, and build systems that are meaningfully harder to attack: even against future quantum-assisted threats.

This project grew out of that thinking. It started as experiments with signatures, evolved into hybrid signing methods, and eventually became a working system that can manage game assets, create value, and run a small economy: all protected with these techniques.

The long-term vision is ambitious: one day, entire systems (including something like a Linux environment) could run using these cryptographic foundations instead of classical ones.

---

## What You Can Do With It Right Now

- Wrap any file or folder into a **PQC-protected container** (`.pqcasset`)
- Use **hybrid signatures** (Falcon + SPHINCS+) for stronger guarantees
- Generate families of keys (Bitcoin, Bitcoin Cash, and custom PQC keys) from a single master key
- Create and manage simple in-game economies protected by these signatures
- Experiment with role-based access and view keys

Everything runs on normal hardware today.

---

## Quick Start 

```bash
git clone https://github.com/DigiMancer3D/PQCAssets.git
cd PQCAssets
make setup && make test
```

That’s it. The `Makefile` will set up the environment, build the necessary binary, and run the full test suite.

---

## Installation

### Normal (Using Make)

```bash
git clone https://github.com/DigiMancer3D/PQCAssets.git
cd PQCAssets
make setup
```

This creates a virtual environment, installs dependencies, and builds the `pah` binary.

### Manual Installation

```bash
git clone https://github.com/DigiMancer3D/PQCAssets.git
cd PQCAssets

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd pah
make          # or: gcc -o pah pah.c -loqs -lm
chmod +x pah
```

---

## Running Tests

After setup, run the master test suite:

```bash
make test
```

Or directly:

```bash
python3 tests/run_full_test_suite.py
```

The test suite checks:
- Key generation (CLI + programmatic)
- Bulk PQC asset wrapping
- Transaction creation (FusionHash + SVC)
- Role system
- End-to-end flow

---

## Troubleshooting

| Problem                              | Likely Cause                          | Fix |
|--------------------------------------|---------------------------------------|-----|
| `ModuleNotFoundError: No module named 'keygen'` | Running from wrong directory or no venv | Run from project root + activate `.venv` |
| `pah` binary not found               | Not built                             | Run `make build` or `cd pah && make` |
| Test data paths fail                 | `pb/bsim/` folder missing             | Some test assets live in `pb/`. The core tests still pass without them |
| Old scripts fail                     | Many old test scripts are outdated    | Use `tests/run_full_test_suite.py` instead |

If you hit issues, run the test suite and share the output. Most problems are path or environment related.

---

## How It Works

At the center is a **master key** (based on a modified SPHINCS+). From this single key the system can derive many different usable keys and signatures.

Instead of using post-quantum algorithms in the standard “textbook” way, PQCAssets combines and reshapes them:

- **Hybrid signatures**: A file can be signed with both FALCON and SPHINCS+ at the same time.
- **Smaller outputs**: SPHINCS+ was tuned to produce much smaller signatures than the default NIST version while keeping strong security properties.
- **Asset containers**: Files and folders can be wrapped into `.pqcasset` containers that carry cryptographic proof of origin and integrity.
- **Economy layer**: A simple game economy can mint, transfer, and burn value using these protected assets and transactions.

The system tries to stay practical: everything must run on normal computers today and produce real, verifiable output.

---

## Project Structure

```
PQCAssets/
├── pah/                    # PQC Asset Handler (C binary + Python wrapper)
│   ├── pah                 # Compiled binary
│   ├── pah.c               # Core wrapping & container logic
│   └── pah_wrap_improved.py# Recommended bulk wrapper
├── keygen/                 # Unified key generation (Sphinx+ master → many families)
├── roles/                  # Role system + Master View Key
├── utils/                  # chain_fusion_tool.py and helpers
├── tests/                  # Master test suite + supporting tests
├── economy/                # Game economy logic and state
├── game/ & grills/         # Game-related code and asset handling
├── pb/                     # Test assets and sprites (optional for core tests)
├── requirements.txt
├── setup.py
├── Makefile                # Main entry point for setup & testing
└── tests/run_full_test_suite.py
```

---

## Key Components

| Component                    | Purpose                                      | Language     |
|-----------------------------|----------------------------------------------|--------------|
| `pah` / `pah_wrap_improved.py` | Wrap files & folders into PQC containers    | C + Python   |
| `keygen/unified_sphinx_keygen.py` | Generate key families from one master key   | Python       |
| `utils/chain_fusion_tool.py`     | Create protected transactions               | Python       |
| `roles/role_system.py`           | Role capabilities + Master View Key         | Python       |
| `tests/run_full_test_suite.py`   | One-command full project test               | Python       |

**Supported output formats:**
- `.pqcasset`: Single wrapped file
- `.pqcasset` containers: Multi-file bundles with per-entry signatures
- Manifest files (`.pqcasset.manifest.json`)
- `.kchain` keychain: The family of signatures

---

## Mathematical Overview

This section is optional. You can stop reading here if you just want to use the tools.

The system builds on two post-quantum signature schemes:

- **SPHINCS+** (stateless hash-based signatures): Very conservative security assumptions. The project uses a tuned version that produces significantly smaller signatures than the default NIST parameter sets while preserving the core security properties.
- **FALCON** (lattice-based signatures): Much smaller and faster signatures. Used for performance-sensitive wrapping.

**Hybrid construction**: Many operations combine both schemes. A file can receive a FALCON signature for speed + a SPHINCS+ signature for long-term assurance. The container format stores both.

Key derivation starts from a single master Sphinx+ key. Child keys for different purposes (Bitcoin-style addresses, custom PQC keys, view keys, etc.) are derived deterministically. This reduces the number of secrets a user must manage.

The economy layer uses these signatures to authorize actions (mint, transfer, burn) in a way that can later be verified mathematically without relying on classical elliptic curve assumptions alone.

---

## Vision & Future Direction

The current system proves that post-quantum techniques can be used practically for:
- Protecting game assets and mods
- Creating verifiable digital scarcity
- Building small economies with cryptographic guarantees

Longer term, the goal is to push these techniques further: toward systems where more of the underlying logic itself can be expressed and verified using post-quantum and non-classical mathematical foundations.

---

## License

BSD-3-Clause (see `LICENSE` file)

---

## Credits & Background

This project grew out of research into practical post-quantum cryptography on classical machines, hybrid signature constructions, and building real systems that can use these tools today rather than waiting for perfect future hardware.

Special thanks to everyone exploring these ideas openly: especially those pushing the conversation around post-quantum standards and their real-world limitations.

---

*Sometimes all we can do is try & be creative. So, I did & I will.*


---

