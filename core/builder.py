import re
from pathlib import Path
from typing import List, Dict, Tuple, Set

INVALID_NAME_CHARS = set('<>:"|?*')
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


def expand_sequence(text: str) -> List[str]:
    """
    Expands expressions like:
      - Episode_{01..12} -> Episode_01 .. Episode_12
      - Section_{1..5} -> Section_1 .. Section_5
      - Part_{A..D} -> Part_A .. Part_D
    """
    pattern = r"\{([0-9]+)\.\.([0-9]+)\}"
    match = re.search(pattern, text)
    if match:
        start_str, end_str = match.group(1), match.group(2)
        start, end = int(start_str), int(end_str)
        width = max(len(start_str), len(end_str)) if start_str.startswith("0") else 0
        step = 1 if start <= end else -1
        results = []
        for i in range(start, end + step, step):
            formatted_num = f"{i:0{width}d}" if width > 0 else str(i)
            expanded = text[:match.start()] + formatted_num + text[match.end():]
            results.extend(expand_sequence(expanded))
        return results

    char_pattern = r"\{([A-Za-z])\.\.([A-Za-z])\}"
    match = re.search(char_pattern, text)
    if match:
        c1, c2 = match.group(1), match.group(2)
        o1, o2 = ord(c1), ord(c2)
        step = 1 if o1 <= o2 else -1
        results = []
        for code in range(o1, o2 + step, step):
            expanded = text[:match.start()] + chr(code) + text[match.end():]
            results.extend(expand_sequence(expanded))
        return results

    return [text]


def parse_folder_names(raw_input: str) -> List[str]:
    """
    Parses multi-line or comma-separated raw input into cleaned folder paths,
    expanding any range sequences.
    """
    names = []
    lines = raw_input.strip().splitlines()
    for line in lines:
        for part in line.split(","):
            cleaned = part.strip().strip('"').strip("'")
            if cleaned:
                # Normalize slashes
                cleaned = cleaned.replace("\\", "/")
                # Strip leading/trailing slashes
                cleaned = cleaned.strip("/")
                if cleaned:
                    expanded = expand_sequence(cleaned)
                    names.extend(expanded)
    
    # Preserve order while removing duplicates
    seen = set()
    deduped = []
    for n in names:
        low = n.lower()
        if low not in seen:
            seen.add(low)
            deduped.append(n)
    return deduped


def validate_subfolder_name(rel_path: str) -> Tuple[bool, str]:
    """
    Validates a relative path for invalid characters or reserved Windows names.
    """
    parts = Path(rel_path).parts
    if not parts:
        return False, "Empty path"

    for part in parts:
        if part in {".", ".."}:
            return False, f"Path component '{part}' is not allowed"
        if any(ch in INVALID_NAME_CHARS for ch in part):
            return False, f"'{part}' contains invalid Windows characters (< > : \" | ? *)"
        stem = part.split(".")[0].upper()
        if stem in RESERVED_NAMES:
            return False, f"'{part}' uses reserved Windows device name ({stem})"
    return True, "Valid"


def preview_creation(base_dir: Path, raw_input: str) -> Dict[str, List[Dict]]:
    names = parse_folder_names(raw_input)
    items = []
    for rel in names:
        is_valid, reason = validate_subfolder_name(rel)
        if not is_valid:
            status = "invalid"
            desc = reason
        else:
            target = base_dir / rel
            if target.exists():
                status = "existing"
                desc = "Already exists (will skip)"
            else:
                status = "new"
                desc = "Ready to create"
        items.append({
            "path": rel,
            "status": status,
            "description": desc
        })
    return {
        "items": items,
        "total": len(items),
        "new": sum(1 for i in items if i["status"] == "new"),
        "existing": sum(1 for i in items if i["status"] == "existing"),
        "invalid": sum(1 for i in items if i["status"] == "invalid")
    }


def execute_create_folders(base_dir: Path, raw_input: str) -> Dict[str, any]:
    preview = preview_creation(base_dir, raw_input)
    created = []
    skipped = []
    failed = []

    for item in preview["items"]:
        rel = item["path"]
        if item["status"] == "invalid":
            failed.append((rel, item["description"]))
            continue
        if item["status"] == "existing":
            skipped.append(rel)
            continue
        try:
            target = base_dir / rel
            target.mkdir(parents=True, exist_ok=True)
            created.append(rel)
        except Exception as exc:
            failed.append((rel, str(exc)))

    return {
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "total": preview["total"]
    }
