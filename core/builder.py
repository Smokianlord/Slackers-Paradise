"""Folder generator engine: one folder per line, validated with fix suggestions.

Commas are *not* separators - they are valid in Windows folder names, so every
non-empty line is exactly one folder (or one nested path when `nested` is on).
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.naming import analyze_name

MAX_EXPANSION = 5000

# Item statuses
NEW = "new"
EXISTING = "existing"
FIXABLE = "fixable"      # has problems, but a clean replacement name is available
INVALID = "invalid"      # has problems and no usable replacement
DUPLICATE = "duplicate"  # same folder already listed on an earlier line


class SequenceTooLarge(ValueError):
    pass


def expand_sequence(text: str, _budget: List[int] = None) -> List[str]:
    """
    Expands expressions like:
      - Episode_{01..12} -> Episode_01 .. Episode_12
      - Section_{1..5}   -> Section_1 .. Section_5
      - Part_{A..D}      -> Part_A .. Part_D
    """
    if _budget is None:
        _budget = [MAX_EXPANSION]

    match = re.search(r"\{(\d+)\.\.(\d+)\}", text)
    if match:
        start_str, end_str = match.group(1), match.group(2)
        start, end = int(start_str), int(end_str)
        if abs(end - start) + 1 > MAX_EXPANSION:
            raise SequenceTooLarge(f"Range {{{start_str}..{end_str}}} is larger than {MAX_EXPANSION} items")
        width = max(len(start_str), len(end_str)) if (start_str.startswith("0") or end_str.startswith("0")) else 0
        step = 1 if start <= end else -1
        results: List[str] = []
        for i in range(start, end + step, step):
            number = f"{i:0{width}d}" if width else str(i)
            results.extend(expand_sequence(text[:match.start()] + number + text[match.end():], _budget))
        return results

    match = re.search(r"\{([A-Za-z])\.\.([A-Za-z])\}", text)
    if match:
        o1, o2 = ord(match.group(1)), ord(match.group(2))
        step = 1 if o1 <= o2 else -1
        results = []
        for code in range(o1, o2 + step, step):
            results.extend(expand_sequence(text[:match.start()] + chr(code) + text[match.end():], _budget))
        return results

    _budget[0] -= 1
    if _budget[0] < 0:
        raise SequenceTooLarge(f"Sequences expand to more than {MAX_EXPANSION} folders")
    return [text]


def _strip_wrapping_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1].strip()
    return text


def parse_lines(raw_input: str, nested: bool = True) -> List[Tuple[int, str]]:
    """
    Turn raw text into (line_number, name) pairs. Every non-empty line is one
    entry; sequence patterns expand into several entries sharing a line number.
    """
    entries: List[Tuple[int, str]] = []
    budget = [MAX_EXPANSION]
    for line_no, line in enumerate(raw_input.splitlines(), start=1):
        text = _strip_wrapping_quotes(line.strip())
        if not text:
            continue
        if nested:
            text = text.replace("\\", "/").strip("/")
            if not text:
                continue
        for name in expand_sequence(text, budget):
            entries.append((line_no, name))
    return entries


def parse_folder_names(raw_input: str, nested: bool = True) -> List[str]:
    """Names only, de-duplicated (case-insensitively) with order preserved."""
    seen = set()
    names = []
    for _, name in parse_lines(raw_input, nested):
        key = name.lower()
        if key not in seen:
            seen.add(key)
            names.append(name)
    return names


def preview_creation(base_dir: Path, raw_input: str, nested: bool = True, apply_fixes: bool = False) -> Dict[str, Any]:
    """
    Analyse every line and report what would happen.

    Each item carries: line, original, suggestion, issues, status, target
    (the relative path that will really be created, or None if skipped).
    """
    try:
        entries = parse_lines(raw_input, nested)
    except SequenceTooLarge as exc:
        return {"items": [], "total": 0, "new": 0, "existing": 0, "fixable": 0,
                "invalid": 0, "duplicate": 0, "error": str(exc)}

    base_len = len(str(base_dir))
    items: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}

    for line_no, original in entries:
        issues, suggestion = analyze_name(original, nested=nested, base_len=base_len)
        normalised = original if nested is False else original.strip("/")
        has_issues = bool(issues)

        if has_issues and not suggestion:
            status, target = INVALID, None
        elif has_issues and not apply_fixes:
            status, target = FIXABLE, None
        else:
            target = suggestion if has_issues else normalised
            status = NEW

        if target:
            key = target.lower()
            if key in seen:
                status, target = DUPLICATE, None
                issues = issues + [f"Same as line {seen[key]}"]
            else:
                seen[key] = line_no
                if (base_dir / target).exists():
                    status = EXISTING

        items.append({
            "line": line_no,
            "original": original,
            "suggestion": suggestion if has_issues else "",
            "issues": issues,
            "status": status,
            "target": target,
            "fixed": has_issues and apply_fixes and bool(target),
        })

    counts = {s: sum(1 for i in items if i["status"] == s) for s in (NEW, EXISTING, FIXABLE, INVALID, DUPLICATE)}
    return {"items": items, "total": len(items), "error": "", **counts}


def apply_suggestions(raw_input: str, nested: bool = True, base_dir: Path = None) -> Tuple[str, int]:
    """
    Rewrite the raw text so every fixable line uses its suggested name.
    Sequence lines are left alone (their expansions are fixed at creation time).
    Returns (new_text, number_of_lines_changed).
    """
    base_len = len(str(base_dir)) if base_dir else 0
    out_lines = []
    changed = 0
    for line in raw_input.splitlines():
        text = _strip_wrapping_quotes(line.strip())
        if not text or re.search(r"\{(?:\d+|[A-Za-z])\.\.(?:\d+|[A-Za-z])\}", text):
            out_lines.append(line)
            continue
        probe = text.replace("\\", "/").strip("/") if nested else text
        issues, suggestion = analyze_name(probe, nested=nested, base_len=base_len)
        if issues and suggestion and suggestion != text:
            out_lines.append(suggestion)
            changed += 1
        else:
            out_lines.append(line)
    return "\n".join(out_lines), changed


def execute_create_folders(base_dir: Path, raw_input: str, nested: bool = True, apply_fixes: bool = False) -> Dict[str, Any]:
    preview = preview_creation(base_dir, raw_input, nested, apply_fixes)
    created: List[str] = []
    created_dirs: List[Path] = []   # every directory this run really made (for undo)
    skipped: List[str] = []
    failed: List[Tuple[str, str]] = []

    for item in preview["items"]:
        status = item["status"]
        if status == EXISTING:
            skipped.append(item["target"])
            continue
        if status != NEW:
            reason = "; ".join(item["issues"]) or status
            failed.append((item["original"], reason))
            continue
        rel = item["target"]
        target = base_dir / rel
        try:
            missing: List[Path] = []
            probe = target
            while probe != base_dir and not probe.exists():
                missing.append(probe)
                probe = probe.parent
            target.mkdir(parents=True, exist_ok=True)
            created.append(rel)
            created_dirs.extend(reversed(missing))
        except Exception as exc:
            failed.append((item["original"], str(exc)))

    return {
        "created": created,
        "created_dirs": created_dirs,
        "skipped": skipped,
        "failed": failed,
        "total": preview["total"],
        "error": preview.get("error", ""),
    }


def undo_created_folders(created_dirs: List[Path]) -> Dict[str, Any]:
    """Remove folders from a previous run - only if they are still empty."""
    removed = 0
    kept: List[str] = []
    for path in reversed(created_dirs):
        try:
            if path.is_dir():
                os.rmdir(path)  # raises if not empty - never deletes user content
                removed += 1
        except OSError:
            kept.append(str(path))
    return {"removed": removed, "kept": kept}
