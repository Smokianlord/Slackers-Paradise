import os
import json
import csv
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DEFAULT_EXCLUDES = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}


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
        low = name.lower()
        return any(fnmatch.fnmatch(low, pat) for pat in patterns)

    if recursive:
        walker = os.walk(root_path)
    else:
        try:
            entries = list(root_path.iterdir())
            dirs = [e.name for e in entries if e.is_dir()]
            files = [e.name for e in entries if e.is_file()]
            walker = [(str(root_path), dirs, files)]
        except Exception as exc:
            raise RuntimeError(f"Cannot read directory: {exc}")

    for dirpath, dirnames, filenames in walker:
        current_dir = Path(dirpath)
        rel_base = current_dir.relative_to(root_path)

        # Filter excluded directories in-place for recursion
        if exclude_system:
            dirnames[:] = [
                d for d in dirnames
                if d not in DEFAULT_EXCLUDES and (include_hidden or not d.startswith("."))
            ]
        elif not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        # Record directories
        if include_dirs and str(rel_base) != ".":
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

        if include_files:
            for fname in sorted(filenames, key=str.lower):
                if not include_hidden and fname.startswith("."):
                    continue
                if not matches_pattern(fname):
                    continue

                fpath = current_dir / fname
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

    return {
        "root": str(root_path),
        "items": items,
        "total_files": file_count,
        "total_dirs": dir_count,
        "total_size_bytes": total_size,
        "total_size_formatted": format_size(total_size),
        "extensions": extension_counts
    }


def generate_ascii_tree(root_path: Path, max_depth: int = 4, exclude_system: bool = True) -> str:
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
            if exclude_system and e.name in DEFAULT_EXCLUDES:
                continue
            if e.name.startswith("."):
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
