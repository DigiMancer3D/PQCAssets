#!/usr/bin/env python3
"""
pah_wrap.py
Phase 4 - Static Asset + Base64 Media Hashed Asset Wrapper

Usage examples:
    python pah_wrap.py myimage.png
    python pah_wrap.py myfolder/ --algorithm sphincs
    python pah_wrap.py audio.wav --base64 --hash
    python pah_wrap.py assets/ --container --name mygameassets

This tool makes it easy to PQC-wrap any static asset (images, maps, json, text, audio, etc.)
and supports an optional "base64 + content hash" mode useful for media that will be
embedded in JSON, metadata, or on-chain records.
"""

import argparse
import os
import sys
import subprocess
import hashlib
import base64
import json
from pathlib import Path
from datetime import datetime, timezone

# ==================== CONFIG ====================
PAH_BINARY = None
DEFAULT_OUTPUT_DIR = find_project_root()  # was Path.home() / "PQCassets" / "pqc_assets"
DEFAULT_ALGORITHM = "falcon"


def find_pah_binary():
    """Robust finder for the pah binary"""
    candidates = [
        find_project_root()  # was Path.home() / "PQCassets" / "pah" / "pah",
        Path.cwd().parent / "pah" / "pah",
        Path.cwd() / "pah" / "pah",
        Path("/home/z0m8i3d/PQCassets/pah/pah"),
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            return str(c)

    # Try walking up from current dir
    p = Path.cwd()
    for _ in range(6):
        cand = p / "pah" / "pah"
        if cand.exists() and os.access(cand, os.X_OK):
            return str(cand)
        p = p.parent

    print("ERROR: Could not find 'pah' binary. Please build it first.")
    sys.exit(1)


def run_pah(cmd):
    """Run pah binary and return success + output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def compute_content_hash(data: bytes) -> str:
    """SHA3-256 content hash (good for media assets)"""
    return hashlib.sha3_256(data).hexdigest()


def wrap_single_file(input_path: Path, output_dir: Path, algorithm: str,
                     use_base64: bool = False, add_hash: bool = False) -> Path:
    """Wrap a single file. Optionally base64 + hash it first."""
    input_path = input_path.resolve()
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    original_data = input_path.read_bytes()
    final_data = original_data
    manifest = {
        "original_filename": input_path.name,
        "original_size": len(original_data),
        "wrapped_at": datetime.now(timezone.utc).isoformat() + "Z",
        "algorithm": algorithm,
        "base64_encoded": use_base64,
        "content_hash": None
    }

    if use_base64:
        final_data = base64.b64encode(original_data)
        manifest["base64"] = True

    if add_hash:
        content_hash = compute_content_hash(original_data)
        manifest["content_hash"] = content_hash
        # Embed hash in filename for easy identification
        hash_suffix = content_hash[:12]
        base_name = f"{input_path.stem}_{hash_suffix}{input_path.suffix}"
    else:
        base_name = input_path.name

    # Write temp file if we modified the data (base64)
    temp_input = input_path
    if use_base64 or add_hash:
        temp_path = output_dir / f".tmp_{input_path.name}"
        temp_path.write_bytes(final_data)
        temp_input = temp_path

    output_name = f"{base_name}.pqcasset"
    output_path = output_dir / output_name

    cmd = [PAH_BINARY, f"--wrap-{algorithm}", str(temp_input), str(output_path)]
    success, output = run_pah(cmd)

    # Cleanup temp
    if temp_input != input_path and temp_input.exists():
        temp_input.unlink()

    if success:
        # Write manifest next to the wrapped file
        manifest_path = output_path.with_suffix(".pqcasset.manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"✅ Wrapped: {output_path}")
        if add_hash:
            print(f"   Content Hash (SHA3-256): {manifest['content_hash']}")
        return output_path
    else:
        print(f"❌ Failed to wrap {input_path}")
        print(output)
        return None


def wrap_folder_as_container(folder: Path, output_dir: Path, name: str, algorithm: str):
    """Wrap an entire folder into one PAH multi-asset container"""
    folder = folder.resolve()
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    container_path = output_dir / f"{name}.pqcasset"

    # Create container
    success, _ = run_pah([PAH_BINARY, "--create-container", str(container_path)])
    if not success:
        print("Failed to create container")
        return None

    added = 0
    for file in folder.rglob("*"):
        if file.is_file():
            success, _ = run_pah([PAH_BINARY, "--add-to-container", str(container_path), str(file)])
            if success:
                added += 1
                print(f"  + {file.name}")
            else:
                print(f"  ! Failed to add {file.name}")

    print(f"\n✅ Created container with {added} assets: {container_path}")
    return container_path


def main():
    global PAH_BINARY
    PAH_BINARY = find_pah_binary()

    parser = argparse.ArgumentParser(
        description="PAH Static Asset & Base64 Media Hashed Asset Wrapper (Phase 4)"
    )
    parser.add_argument("input", help="File or folder to wrap")
    parser.add_argument("--algorithm", choices=["falcon", "sphincs", "hybrid"],
                        default=DEFAULT_ALGORITHM, help="PQC algorithm (default: falcon)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Where to put wrapped assets")
    parser.add_argument("--base64", action="store_true",
                        help="Base64 encode the asset before wrapping (good for media in JSON)")
    parser.add_argument("--hash", action="store_true",
                        help="Compute and embed SHA3-256 content hash")
    parser.add_argument("--container", action="store_true",
                        help="Wrap entire folder as one PAH multi-asset container")
    parser.add_argument("--name", help="Name for container (required with --container)")

    args = parser.parse_args()

    input_path = Path(args.input)

    if args.container:
        if not args.name:
            print("ERROR: --name is required when using --container")
            sys.exit(1)
        wrap_folder_as_container(input_path, args.output_dir, args.name, args.algorithm)
    else:
        if input_path.is_file():
            wrap_single_file(input_path, args.output_dir, args.algorithm,
                             use_base64=args.base64, add_hash=args.hash)
        elif input_path.is_dir():
            print("Wrapping folder as individual files...")
            for f in input_path.rglob("*"):
                if f.is_file():
                    wrap_single_file(f, args.output_dir, args.algorithm,
                                     use_base64=args.base64, add_hash=args.hash)
        else:
            print(f"ERROR: {input_path} is not a file or directory")
            sys.exit(1)


if __name__ == "__main__":
    main()
