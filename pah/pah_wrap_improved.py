#!/usr/bin/env python3
"""
pah_wrap_improved.py - Bulk PQC Asset Wrapper for PQCassets Project
Phase 4/5 Static Asset + Containerized PQC Zip-Style Storage

Wraps files or entire folders using Falcon, SPHINCS+, or Hybrid via the pah C binary.
Produces .pqcasset files or multi-asset containers (PQC-protected zip style).

This is the main recommended tool. The old pah_wrap.py can be archived.
"""

import argparse
import os
import sys
import subprocess
import hashlib
import base64
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# ==================== CONFIG ====================
DEFAULT_OUTPUT_DIR = Path("pqc_wrapped")
DEFAULT_ALGORITHM = "falcon"
SUPPORTED_ALGORITHMS = ["falcon", "sphincs", "hybrid"]


def find_project_root(start: Path = None) -> Path:
    """Robust project root finder for PQCassets (handles legacy new_thing too)."""
    if start is None:
        start = Path.cwd()
    markers = ["PQCassets", ".git", "pah", "keygen", "setup.py", "economy"]
    p = start.resolve()
    for _ in range(8):
        for marker in markers:
            if (p / marker).exists():
                return p
        if p.parent == p:
            break
        p = p.parent
    return start


def find_pah_binary() -> str:
    """Robust finder for the compiled pah binary."""
    project_root = find_project_root()
    candidates: List[Path] = [
        project_root / "pah" / "pah",
        project_root.parent / "pah" / "pah",
        Path.cwd() / "pah" / "pah",
        Path.cwd().parent / "pah" / "pah",
        Path.home() / "PQCassets" / "pah" / "pah",
        # Legacy support (safe - only used if the above fail)
        Path.home() / "new_thing" / "pah" / "pah",          # legacy fallback
        Path("/home/z0m8i3d/PQCassets/pah/pah"),
        Path("/home/z0m8i3d/new_thing/pah/pah"),            # legacy fallback
    ]

    # Walk upwards from script / cwd / project root
    for base in [Path(__file__).parent, Path.cwd(), project_root]:
        for _ in range(6):
            cand = base / "pah" / "pah"
            if cand.exists() and os.access(cand, os.X_OK):
                return str(cand.resolve())
            if base.parent == base:
                break
            base = base.parent

    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            return str(c.resolve())

    print("ERROR: Could not find executable 'pah' binary.")
    print("Please build it first: cd pah && make")
    sys.exit(1)


def run_pah(cmd: List[str], timeout: int = 180) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as e:
        return False, str(e)


def compute_content_hash(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def wrap_single_file(
    input_path: Path,
    output_dir: Path,
    algorithm: str,
    use_base64: bool = False,
    add_hash: bool = False,
    quiet: bool = False,
) -> Optional[Path]:
    input_path = input_path.resolve()
    if not input_path.exists() or not input_path.is_file():
        if not quiet:
            print(f"ERROR: File not found: {input_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    original_data = input_path.read_bytes()
    final_data = original_data

    manifest = {
        "original_filename": input_path.name,
        "original_path": str(input_path),
        "original_size": len(original_data),
        "wrapped_at": datetime.now(timezone.utc).isoformat() + "Z",
        "algorithm": algorithm,
        "base64_encoded": use_base64,
        "content_hash": None,
        "pah_wrapper_version": "2.0-clean",
    }

    if use_base64:
        final_data = base64.b64encode(original_data)

    if add_hash:
        content_hash = compute_content_hash(original_data)
        manifest["content_hash"] = content_hash
        hash_suffix = content_hash[:12]
        base_name = f"{input_path.stem}_{hash_suffix}{input_path.suffix}"
    else:
        base_name = input_path.name

    temp_input = input_path
    temp_path = None
    if use_base64 or add_hash:
        temp_path = output_dir / f".tmp_{input_path.name}"
        temp_path.write_bytes(final_data)
        temp_input = temp_path

    output_name = f"{base_name}.pqcasset"
    output_path = output_dir / output_name

    cmd = [find_pah_binary(), f"--wrap-{algorithm}", str(temp_input), str(output_path)]
    success, output = run_pah(cmd)

    if temp_path and temp_path.exists():
        temp_path.unlink()

    if success:
        manifest_path = output_path.with_suffix(".pqcasset.manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2))
        if not quiet:
            print(f"✅ Wrapped ({algorithm}): {output_path.name}")
            if add_hash:
                print(f"   Content Hash: {manifest['content_hash']}")
        return output_path
    else:
        if not quiet:
            print(f"❌ Failed to wrap {input_path.name}")
        return None


def wrap_folder_as_container(
    folder: Path,
    output_dir: Path,
    name: str,
    algorithm: str,
    keep_temps: bool = False,
    quiet: bool = False,
) -> Optional[Path]:
    folder = folder.resolve()
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    container_path = output_dir / f"{name}.pqcasset"

    temp_dir = Path(tempfile.mkdtemp(prefix="pqc_prewrap_"))
    if not quiet:
        print(f"Creating PQC container '{name}' using algorithm={algorithm}")

    prewrapped: List[Path] = []
    files = [f for f in folder.rglob("*") if f.is_file()]
    total = len(files)

    for i, f in enumerate(files, 1):
        if not quiet:
            print(f"  [{i}/{total}] Pre-wrapping {f.name} ...", end=" ")
        wrapped = wrap_single_file(f, temp_dir, algorithm, use_base64=False, add_hash=True, quiet=True)
        if wrapped:
            prewrapped.append(wrapped)
            if not quiet:
                print("✓")
        else:
            if not quiet:
                print("✗")

    if not prewrapped:
        print("No files successfully pre-wrapped. Aborting.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    success, _ = run_pah([find_pah_binary(), "--create-container", str(container_path)])
    if not success:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    added = 0
    container_manifest_entries = []

    for i, wrapped_file in enumerate(prewrapped, 1):
        success, _ = run_pah([find_pah_binary(), "--add-to-container", str(container_path), str(wrapped_file)])
        if success:
            added += 1
            if not quiet:
                print(f"  + [{i}/{len(prewrapped)}] {wrapped_file.name} -> container")
            try:
                mf_path = wrapped_file.with_suffix(".pqcasset.manifest.json")
                mf = json.loads(mf_path.read_text()) if mf_path.exists() else {}
            except Exception:
                mf = {}
            container_manifest_entries.append({
                "entry_index": added - 1,
                "stored_filename": wrapped_file.name,
                "original_filename": mf.get("original_filename"),
                "inner_algorithm": algorithm,
                "inner_content_hash": mf.get("content_hash"),
            })
        else:
            if not quiet:
                print(f"  ! Failed to add {wrapped_file.name}")

    container_manifest = {
        "container_name": name,
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "total_entries": added,
        "inner_algorithm": algorithm,
        "entries": container_manifest_entries,
        "note": "Each entry pre-wrapped with chosen algorithm + outer Falcon container sig",
    }
    manifest_path = container_path.with_suffix(".pqcasset.container.manifest.json")
    manifest_path.write_text(json.dumps(container_manifest, indent=2))

    if not keep_temps:
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print(f"Pre-wrapped files kept in: {temp_dir}")

    if not quiet:
        print(f"\n✅ PQC Zip Container created: {container_path}")
        print(f"   Entries: {added} | Inner: {algorithm} | Outer per-entry: Falcon")

    return container_path


def main():
    parser = argparse.ArgumentParser(
        description="PAH Bulk PQC Wrapper (Falcon / SPHINCS+ / Hybrid) for PQCassets"
    )
    parser.add_argument("input", help="File or folder to wrap")
    parser.add_argument("--algorithm", choices=SUPPORTED_ALGORITHMS, default=DEFAULT_ALGORITHM)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base64", action="store_true")
    parser.add_argument("--hash", action="store_true")
    parser.add_argument("--container", action="store_true")
    parser.add_argument("--name", help="Container name (required with --container)")
    parser.add_argument("--keep-temps", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")

    args = parser.parse_args()
    input_path = Path(args.input).resolve()

    if args.container:
        if not args.name:
            print("ERROR: --name is required with --container")
            sys.exit(1)
        wrap_folder_as_container(input_path, args.output_dir, args.name, args.algorithm,
                                 keep_temps=args.keep_temps, quiet=args.quiet)
    else:
        if input_path.is_file():
            wrap_single_file(input_path, args.output_dir, args.algorithm,
                             use_base64=args.base64, add_hash=args.hash, quiet=args.quiet)
        elif input_path.is_dir():
            if not args.quiet:
                print(f"Wrapping folder as individual files ({args.algorithm})...")
            for f in input_path.rglob("*"):
                if f.is_file():
                    wrap_single_file(f, args.output_dir, args.algorithm,
                                     use_base64=args.base64, add_hash=args.hash, quiet=args.quiet)
        else:
            print(f"ERROR: {input_path} is not a file or directory")
            sys.exit(1)


if __name__ == "__main__":
    main()
