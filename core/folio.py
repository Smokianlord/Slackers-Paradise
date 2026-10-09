import os
import io
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


def generate_ascii_tree(scan_result: Dict[str, Any], show_sizes: bool = True) -> str:
    """Render the scanned items (respecting every scan filter) as an ASCII tree."""
    root_name = Path(scan_result["root"]).name or scan_result["root"]
    tree: Dict[str, Any] = {}
    for item in scan_result["items"]:
        node = tree
        parts = item["relative_path"].split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {"__dir__": True, "__kids__": {}})["__kids__"]
        leaf = node.setdefault(parts[-1], {"__kids__": {}})
        leaf["__dir__"] = item["is_dir"]
        leaf["__size__"] = item["size_formatted"]

    lines = [f"{root_name}/"]

    def walk(kids: Dict[str, Any], prefix: str):
        ordered = sorted(kids.items(), key=lambda kv: (not kv[1].get("__dir__", False), kv[0].lower()))
        for i, (name, node) in enumerate(ordered):
            last = i == len(ordered) - 1
            if node.get("__dir__"):
                label = f"{name}/"
            else:
                label = f"{name} ({node['__size__']})" if show_sizes else name
            lines.append(f"{prefix}{'└── ' if last else '├── '}{label}")
            if node["__kids__"]:
                walk(node["__kids__"], prefix + ("    " if last else "│   "))

    walk(tree, "")
    return "\n".join(lines)


def _csv_text(items: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["Name", "Relative Path", "Type", "Extension", "Size Bytes", "Size Formatted", "Modified"])
    for item in items:
        writer.writerow([item["name"], item["relative_path"], item["type"], item["extension"],
                         item["size_bytes"], item["size_formatted"], item["modified"]])
    return buf.getvalue()


def render_scan_data(scan_result: Dict[str, Any], format_type: str) -> str:
    """Render a scan in one of: txt, tree, csv, json, markdown."""
    fmt = format_type.lower()
    items = scan_result["items"]

    if fmt == "txt":
        return "\n".join(item["relative_path"] for item in items)
    if fmt == "tree":
        return generate_ascii_tree(scan_result)
    if fmt == "csv":
        return _csv_text(items)
    if fmt == "json":
        return json.dumps({
            "root": scan_result["root"],
            "generated": datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "files": scan_result["total_files"],
                "folders": scan_result["total_dirs"],
                "total_size": scan_result["total_size_formatted"],
            },
            "items": items,
        }, indent=2, ensure_ascii=False)
    if fmt == "markdown":
        lines = [
            f"# Directory Catalog: {Path(scan_result['root']).name}",
            "",
            f"**Path**: `{scan_result['root']}`  ",
            f"**Files**: {scan_result['total_files']} | **Folders**: {scan_result['total_dirs']} | **Total Size**: {scan_result['total_size_formatted']}  ",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| Item | Type | Size | Modified | Path |",
            "|---|---|---|---|---|",
        ]
        for item in items:
            name = item["name"].replace("|", "\\|")
            rpath = item["relative_path"].replace("|", "\\|")
            lines.append(f"| {name} | {item['type']} | {item['size_formatted']} | {item['modified']} | `{rpath}` |")
        return "\n".join(lines)
    raise ValueError(f"Unsupported format: {format_type}")


def export_scan_data(scan_result: Dict[str, Any], output_path: Path, format_type: str) -> None:
    text = render_scan_data(scan_result, format_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel opens CSV with correct accents/CJK; harmless elsewhere
    encoding = "utf-8-sig" if format_type.lower() == "csv" else "utf-8"
    with open(output_path, "w", encoding=encoding, newline="") as f:
        f.write(text)
