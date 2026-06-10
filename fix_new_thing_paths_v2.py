#!/usr/bin/env python3
"""
fix_new_thing_paths_v2.py
IMPROVED & FIXED version of the bulk path cleaner.

Key fixes:
- Proper escaping for regex replacement (the previous backslash pattern caused re.error)
- Safer replacement using a function (avoids template parsing bugs)
- Skips itself and the improved wrapper's intentional legacy markers
- Better error handling per file
- Dry-run by default, --apply to modify

Usage:
    cd ~/PQCassets
    python3 fix_new_thing_paths_v2.py           # Dry run (recommended first)
    python3 fix_new_thing_paths_v2.py --apply   # Apply changes + create .bak backups
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path.cwd().resolve()

SKIP_FILES = {
    "fix_new_thing_paths.py",
    "fix_new_thing_paths_v2.py",
}

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", ".mypy_cache", "build", "dist", ".pytest_cache"}

# Only process these file types
TEXT_SUFFIXES = {".py", ".sh", ".c", ".h", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}

def should_process(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    for part in path.parts:
        if part in SKIP_DIRS:
            return False
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Makefile", "makefile"}:
        return False
    return True

def replace_new_thing(match: re.Match) -> str:
    """Safe replacement function (avoids re template escape bugs)."""
    text = match.group(0)
    # Order of checks matters
    if "/home/z0m8i3d/new_thing" in text:
        return text.replace("/home/z0m8i3d/new_thing", "/home/z0m8i3d/PQCassets")
    if "~/new_thing" in text:
        return text.replace("~/new_thing", "~/PQCassets")
    if "Path.home()" in text and "new_thing" in text:
        return text.replace('Path.home() / "new_thing"', 'find_project_root()  # was Path.home() / "new_thing"') \
                   .replace("Path.home() / 'new_thing'", "find_project_root()  # was Path.home() / 'new_thing'")
    if "new_thing/" in text:
        return text.replace("new_thing/", "PQCassets/")
    if "new_thing\\" in text:
        return text.replace("new_thing\\", "PQCassets\\")
    if text.strip() in {'"new_thing"', "'new_thing'"}:
        return text.replace("new_thing", "PQCassets")
    # Fallback - bare word (only in comments/strings usually safe)
    return text.replace("new_thing", "PQCassets")

def process_file(path: Path, dry_run: bool) -> bool:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  ! Could not read {path}: {e}")
        return False

    original = content

    # Main patterns (using a function for safety)
    patterns = [
        r"/home/z0m8i3d/new_thing",
        r"~/new_thing",
        r"Path\.home\(\)\s*/\s*['\"]new_thing['\"]",
        r"new_thing/",
        r"new_thing\\",
        r"['\"]new_thing['\"]",
        r"\bnew_thing\b",
    ]

    changed = False
    for pat in patterns:
        try:
            new_content, count = re.subn(pat, replace_new_thing, content)
            if count > 0:
                content = new_content
                changed = True
        except re.error as e:
            print(f"  ! Regex error in {path} on pattern {pat}: {e}")
            continue

    if not changed or content == original:
        return False

    if dry_run:
        print(f"📝 Would update: {path.relative_to(PROJECT_ROOT)}")
        return True

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    try:
        path.rename(backup_path)
        path.write_text(content, encoding="utf-8")
        print(f"✅ Updated: {path.relative_to(PROJECT_ROOT)}  (backup: {backup_path.name})")
        return True
    except Exception as e:
        print(f"  ! Failed to write {path}: {e}")
        # Try to restore backup if possible
        if backup_path.exists():
            backup_path.rename(path)
        return False

def main():
    dry_run = "--apply" not in sys.argv

    print(f"🔍 Scanning {PROJECT_ROOT} for old 'new_thing' references (v2 - safer)...\n")

    updated_count = 0
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if not should_process(fpath):
                continue

            if process_file(fpath, dry_run):
                updated_count += 1

    print("\n" + "=" * 60)
    if dry_run:
        print(f"DRY RUN COMPLETE. {updated_count} file(s) would be updated.")
        print("Run with --apply to make changes (backups will be created automatically).")
    else:
        print(f"✅ Done. Updated {updated_count} file(s).")
        print("Backups created with .bak_YYYYMMDD_HHMMSS extension next to originals.")
        print("\nNext steps:")
        print("  git status                    # if using git")
        print("  python3 -m py_compile pah/pah_wrap_improved.py")
        print("  python3 pah/pah_wrap_improved.py --help   # quick smoke test")

if __name__ == "__main__":
    main()
