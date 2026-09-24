import os
import json
import csv
import fnmatch
import ctypes
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DEFAULT_EXCLUDES = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}


def is_hidden_or_system(path: Path) -> bool:
    name = path.name
    if name.startswith("."):
        return True
    if name.lower() in {"desktop.ini", "thumbs.db", "ntuser.dat", "ntuser.ini"}:
        return True
    if os.name == "nt":
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and (attrs & (0x2 | 0x4)):  # FILE_ATTRIBUTE_HIDDEN (0x2) or FILE_ATTRIBUTE_SYSTEM (0x4)
                return True
        except Exception:
            pass
    return False


def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"


def scan_directory(
    root_path: Path,
    recursive: bool = False,
    include_files: bool = True,
    include_dirs: bool = True,
    include_hidden: bool = False,
    patterns: Optional[List[str]] = None,
    exclude_system: bool = True
) -> Dict[str, Any]:
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Directory not found: {root_path}")

    items = []
    total_size = 0
    file_count = 0
    dir_count = 0
    extension_counts = {}

    patterns = [p.strip().lower() for p in patterns if p.strip()] if patterns else ["*"]

    def matches_pattern(name: str) -> bool:
        if not patterns or "*" in patterns or "*.*" in patterns:
            return True
        low = name.lower()
        return any(fnmatch.fnmatch(low, pat) for pat in patterns)

    def should_skip(p: Path) -> bool:
        if not include_hidden and is_hidden_or_system(p):
            return True
        if exclude_system and p.name in DEFAULT_EXCLUDES:
            return True
        return False

    if not recursive:
        # Non-recursive: direct scan of root_path entries
        try:
            entries = sorted(list(root_path.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
        except Exception as exc:
            raise RuntimeError(f"Cannot read directory: {exc}")

        for entry in entries:
            if should_skip(entry):
                continue

            rel_path = entry.relative_to(root_path)

            if entry.is_dir():
                if include_dirs:
                    try:
                        stat = entry.stat()
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        mtime = "-"
                    items.append({
                        "name": entry.name,
                        "relative_path": str(rel_path).replace("\\", "/"),
                        "is_dir": True,
                        "type": "Folder",
                        "size_bytes": 0,
                        "size_formatted": "-",
                        "extension": "",
                        "modified": mtime
                    })
                    dir_count += 1
            elif entry.is_file():
                if include_files and matches_pattern(entry.name):
                    try:
                        stat = entry.stat()
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        size = 0
                        mtime = "-"
                    ext = entry.suffix.lower()
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1
                    total_size += size
                    file_count += 1
                    items.append({
                        "name": entry.name,
                        "relative_path": str(rel_path).replace("\\", "/"),
                        "is_dir": False,
                        "type": ext.upper() if ext else "File",
                        "size_bytes": size,
                        "size_formatted": format_size(size),
                        "extension": ext,
                        "modified": mtime
                    })
    else:
        # Recursive: walk root_path
        for dirpath, dirnames, filenames in os.walk(root_path):
            current_dir = Path(dirpath)

            # Filter dirnames in-place so os.walk does not recurse into skipped directories
            filtered_dirnames = []
            for d in dirnames:
                p = current_dir / d
                if not should_skip(p):
                    filtered_dirnames.append(d)
            dirnames[:] = filtered_dirnames

            # Record directories in current_dir
            if include_dirs and current_dir != root_path:
                rel_base = current_dir.relative_to(root_path)
                try:
                    stat = current_dir.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    mtime = "-"
                items.append({
                    "name": current_dir.name,
                    "relative_path": str(rel_base).replace("\\", "/"),
                    "is_dir": True,
                    "type": "Folder",
                    "size_bytes": 0,
                    "size_formatted": "-",
                    "extension": "",
                    "modified": mtime
                })
                dir_count += 1

            # Record files in current_dir
            if include_files:
                for fname in sorted(filenames, key=str.lower):
                    fpath = current_dir / fname
                    if should_skip(fpath):
                        continue
                    if not matches_pattern(fname):
                        continue

                    rel_fpath = fpath.relative_to(root_path)
                    try:
                        stat = fpath.stat()
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        size = 0
                        mtime = "-"

                    ext = fpath.suffix.lower()
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1
                    total_size += size
                    file_count += 1

                    items.append({
                        "name": fname,
                        "relative_path": str(rel_fpath).replace("\\", "/"),
                        "is_dir": False,
                        "type": ext.upper() if ext else "File",
                        "size_bytes": size,
                        "size_formatted": format_size(size),
                        "extension": ext,
                        "modified": mtime
                    })

    # Sort items: folders first, then files alphabetically by relative path
    items.sort(key=lambda it: (not it["is_dir"], it["relative_path"].lower()))

    return {
        "root": str(root_path),
        "items": items,
        "total_files": file_count,
        "total_dirs": dir_count,
        "total_size_bytes": total_size,
        "total_size_formatted": format_size(total_size),
        "extensions": extension_counts
    }


def generate_ascii_tree(root_path: Path, max_depth: int = 4, exclude_system: bool = True, include_hidden: bool = False) -> str:
    lines = [f"{root_path.name}/"]

    def walk_tree(dir_path: Path, prefix: str = "", depth: int = 0):
        if depth >= max_depth:
            return
        try:
            entries = sorted(list(dir_path.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception:
            return

        filtered = []
        for e in entries:
            if not include_hidden and is_hidden_or_system(e):
                continue
            if exclude_system and e.name in DEFAULT_EXCLUDES:
                continue
            filtered.append(e)

        total = len(filtered)
        for i, entry in enumerate(filtered):
            is_last = (i == total - 1)
            connector = "└── " if is_last else "├── "
            extension_str = f" ({format_size(entry.stat().st_size)})" if entry.is_file() else "/"
            lines.append(f"{prefix}{connector}{entry.name}{extension_str}")
            if entry.is_dir():
                sub_prefix = prefix + ("    " if is_last else "│   ")
                walk_tree(entry, sub_prefix, depth + 1)

    walk_tree(root_path)
    return "\n".join(lines)


def export_scan_data(scan_result: Dict[str, Any], output_path: Path, format_type: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = format_type.lower()
    items = scan_result["items"]

    if fmt == "txt":
        lines = [item["relative_path"] for item in items]
        output_path.write_text("\n".join(lines), encoding="utf-8")

    elif fmt == "tree":
        root = Path(scan_result["root"])
        tree_text = generate_ascii_tree(root)
        output_path.write_text(tree_text, encoding="utf-8")

    elif fmt == "csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Relative Path", "Type", "Extension", "Size Bytes", "Size Formatted", "Modified"])
            for item in items:
                writer.writerow([
                    item["name"],
                    item["relative_path"],
                    item["type"],
                    item["extension"],
                    item["size_bytes"],
                    item["size_formatted"],
                    item["modified"]
                ])

    elif fmt == "json":
        data = {
            "root": scan_result["root"],
            "summary": {
                "files": scan_result["total_files"],
                "folders": scan_result["total_dirs"],
                "total_size": scan_result["total_size_formatted"]
            },
            "items": items
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    elif fmt == "markdown":
        lines = [
            f"# Directory Catalog: {Path(scan_result['root']).name}",
            "",
            f"**Path**: `{scan_result['root']}`  ",
            f"**Total Files**: {scan_result['total_files']} | **Folders**: {scan_result['total_dirs']} | **Total Size**: {scan_result['total_size_formatted']}  ",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| Item | Type | Size | Modified | Path |",
            "|---|---|---|---|---|"
        ]
        for item in items:
            name = item["name"].replace("|", "\\|")
            rpath = item["relative_path"].replace("|", "\\|")
            lines.append(f"| {name} | {item['type']} | {item['size_formatted']} | {item['modified']} | `{rpath}` |")
        output_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported format: {format_type}")
