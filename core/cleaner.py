import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple
from core.folio import format_size
from core.shortcuts import resolve_lnk_target


def scan_user_temp() -> List[Dict[str, Any]]:
    temp_dir = os.environ.get("TEMP") or os.environ.get("TMP")
    if not temp_dir or not os.path.isdir(temp_dir):
        return []

    items = []
    p = Path(temp_dir)
    try:
        for entry in p.iterdir():
            try:
                if entry.is_file():
                    size = entry.stat().st_size
                    items.append({
                        "path": entry,
                        "name": entry.name,
                        "category": "User Temp File",
                        "size_bytes": size,
                        "size_formatted": format_size(size),
                        "is_dir": False,
                        "selected": True
                    })
                elif entry.is_dir():
                    # Calculate directory size
                    dir_size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
                    items.append({
                        "path": entry,
                        "name": entry.name,
                        "category": "User Temp Folder",
                        "size_bytes": dir_size,
                        "size_formatted": format_size(dir_size),
                        "is_dir": True,
                        "selected": True
                    })
            except Exception:
                continue
    except Exception:
        pass
    return items


def scan_empty_folders(target_dir: Path) -> List[Dict[str, Any]]:
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    empty_dirs = []
    for dirpath, dirnames, filenames in os.walk(target_dir, topdown=False):
        p = Path(dirpath)
        if p == target_dir:
            continue
        try:
            # Check if directory has no files and no subdirectories
            if not any(p.iterdir()):
                empty_dirs.append({
                    "path": p,
                    "name": p.name,
                    "category": "Empty Folder",
                    "size_bytes": 0,
                    "size_formatted": "0 B",
                    "is_dir": True,
                    "selected": True
                })
        except Exception:
            continue
    return empty_dirs


def scan_broken_shortcuts(target_dir: Path) -> List[Dict[str, Any]]:
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    broken = []
    for entry in target_dir.rglob("*.lnk"):
        if entry.is_file():
            info = resolve_lnk_target(entry)
            if not info["valid"] and info["target"]:
                try:
                    size = entry.stat().st_size
                except Exception:
                    size = 0
                broken.append({
                    "path": entry,
                    "name": entry.name,
                    "category": f"Broken Shortcut -> {info['target'][:30]}...",
                    "size_bytes": size,
                    "size_formatted": format_size(size),
                    "is_dir": False,
                    "selected": True
                })
    return broken


def execute_clean(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    cleaned = 0
    freed_bytes = 0
    skipped = 0
    failed = []

    for item in items:
        if not item.get("selected", True):
            continue
        p: Path = item["path"]
        try:
            if not p.exists():
                skipped += 1
                continue
            if item["is_dir"]:
                shutil.rmtree(p, ignore_errors=False)
            else:
                p.unlink()
            cleaned += 1
            freed_bytes += item.get("size_bytes", 0)
        except Exception as exc:
            skipped += 1
            failed.append((p.name, str(exc)))

    return {
        "cleaned": cleaned,
        "freed_bytes": freed_bytes,
        "freed_formatted": format_size(freed_bytes),
        "skipped": skipped,
        "failed": failed
    }
