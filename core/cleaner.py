import ctypes
import os
import shutil
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.folio import DEFAULT_EXCLUDES, format_size, is_hidden_or_system
from core.shortcuts import resolve_lnk_target

CAT_TEMP_FILE = "Temp file"
CAT_TEMP_FOLDER = "Temp folder"
CAT_EMPTY = "Empty folder"
CAT_BROKEN = "Broken shortcut"
RECYCLABLE = {CAT_EMPTY, CAT_BROKEN}   # temp files are junk - recycling them would only waste disk


# ----------------------------------------------------------------- safety
def is_protected_root(path: Path) -> bool:
    """Drive roots, the user profile and system folders must never be swept wholesale."""
    try:
        resolved = path.resolve()
    except OSError:
        return True
    if resolved == Path(resolved.anchor):
        return True
    protected = {Path.home().resolve()}
    for var in ("WINDIR", "PROGRAMFILES", "PROGRAMFILES(X86)", "SYSTEMROOT", "PROGRAMDATA"):
        value = os.environ.get(var)
        if value:
            protected.add(Path(value).resolve())
    return resolved in protected


# ------------------------------------------------------------ recycle bin
class _SHFILEOPSTRUCTW(ctypes.Structure):
    _pack_ = 1 if sys.maxsize <= 2**32 else 8
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def send_to_recycle_bin(path: Path) -> None:
    """Move a file/folder to the Windows Recycle Bin. Raises OSError on failure."""
    if os.name != "nt":
        raise OSError("Recycle Bin is only available on Windows")
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = _SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = str(path) + "\0"          # ctypes appends the second terminating NUL
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if result != 0 or op.fAnyOperationsAborted:
        raise OSError(f"Windows could not move this item to the Recycle Bin (code {result})")


# ---------------------------------------------------------------- scanners
def _tree_stats(path: Path):
    """(total_size, newest_mtime) of everything below `path`."""
    size, newest = 0, 0.0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        else:
                            st = entry.stat(follow_symlinks=False)
                            size += st.st_size
                            newest = max(newest, st.st_mtime)
                    except OSError:
                        continue
        except OSError:
            continue
    return size, newest


def _item(path: Path, category: str, size: int, is_dir: bool, detail: str = "") -> Dict[str, Any]:
    return {
        "path": path,
        "name": path.name,
        "category": category,
        "detail": detail,
        "size_bytes": size,
        "size_formatted": format_size(size) if size else "-",
        "is_dir": is_dir,
        "selected": True,
    }


def scan_user_temp(min_age_hours: float = 24.0) -> List[Dict[str, Any]]:
    """Items in %TEMP% not touched for `min_age_hours` (newer ones are likely in use)."""
    temp_dir = os.environ.get("TEMP") or os.environ.get("TMP")
    if not temp_dir or not os.path.isdir(temp_dir):
        return []
    cutoff = time.time() - min_age_hours * 3600
    items: List[Dict[str, Any]] = []
    try:
        entries = list(os.scandir(temp_dir))
    except OSError:
        return []
    for entry in entries:
        try:
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                size, newest = _tree_stats(path)
                newest = max(newest, entry.stat().st_mtime)
                if newest <= cutoff:
                    items.append(_item(path, CAT_TEMP_FOLDER, size, True))
            else:
                st = entry.stat(follow_symlinks=False)
                if st.st_mtime <= cutoff:
                    items.append(_item(path, CAT_TEMP_FILE, st.st_size, False))
        except OSError:
            continue
    items.sort(key=lambda it: -it["size_bytes"])
    return items


def scan_empty_folders(target_dir: Path) -> List[Dict[str, Any]]:
    """
    Top-most folders that contain nothing but other empty folders.
    (Removing one removes its whole empty subtree in a single step.)
    """
    if not target_dir.is_dir() or is_protected_root(target_dir):
        return []

    result: List[Path] = []

    def visit(path: Path) -> bool:
        """True if `path` is effectively empty."""
        try:
            entries = list(os.scandir(path))
        except OSError:
            return False
        empty_kids: List[Path] = []
        blocked = False
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    child = Path(entry.path)
                    if entry.name in DEFAULT_EXCLUDES or is_hidden_or_system(child):
                        blocked = True
                    elif visit(child):
                        empty_kids.append(child)
                    else:
                        blocked = True
                else:
                    blocked = True
            except OSError:
                blocked = True
        if blocked:
            result.extend(empty_kids)
            return False
        return True

    if visit(target_dir):
        return []  # the chosen folder itself is empty; never offer to delete it
    return [_item(p, CAT_EMPTY, 0, True) for p in sorted(result, key=lambda p: str(p).lower())]


def scan_broken_shortcuts(target_dir: Path) -> List[Dict[str, Any]]:
    if not target_dir.is_dir() or is_protected_root(target_dir):
        return []
    broken = []
    for dirpath, dirnames, filenames in os.walk(target_dir):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDES]
        for fname in filenames:
            if not fname.lower().endswith(".lnk"):
                continue
            entry = Path(dirpath) / fname
            info = resolve_lnk_target(entry)
            if info["resolved"] and not info["valid"] and info["target"]:
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                broken.append(_item(entry, CAT_BROKEN, size, False, detail=f"Missing: {info['target']}"))
    return broken


# ----------------------------------------------------------------- execute
def execute_clean(items: List[Dict[str, Any]], use_recycle_bin: bool = True) -> Dict[str, Any]:
    cleaned = freed_bytes = skipped = 0
    failed: List[Any] = []

    for item in items:
        if not item.get("selected", True):
            continue
        path: Path = item["path"]
        try:
            if not path.exists() and not path.is_symlink():
                skipped += 1
                continue
            if use_recycle_bin and item["category"] in RECYCLABLE:
                send_to_recycle_bin(path)
            elif item["is_dir"]:
                shutil.rmtree(path)
            else:
                path.unlink()
            cleaned += 1
            freed_bytes += item.get("size_bytes", 0)
        except Exception as exc:
            skipped += 1
            failed.append((path.name, str(exc)))

    return {
        "cleaned": cleaned,
        "freed_bytes": freed_bytes,
        "freed_formatted": format_size(freed_bytes),
        "skipped": skipped,
        "failed": failed,
    }
