"""Windows-safe file and folder name validation with automatic fix suggestions.

Shared by Build-a-Folder (new folder names) and RenameRoulette (proposed file names).
"""
import re
from typing import List, Tuple

INVALID_NAME_CHARS = set('<>:"|?*')
SEPARATORS = ("/", "\\")
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
MAX_COMPONENT_LEN = 255
MAX_PATH_LEN = 259  # classic MAX_PATH (260) minus the terminating NUL


def _is_control(ch: str) -> bool:
    return ord(ch) < 32


def check_component(name: str, allow_separators: bool = False) -> List[str]:
    """Return a list of human readable problems with a single path component."""
    problems: List[str] = []
    if not name.strip():
        return ["Name is empty"]

    bad = sorted({ch for ch in name if ch in INVALID_NAME_CHARS})
    if not allow_separators:
        bad += sorted({ch for ch in name if ch in SEPARATORS})
    if bad:
        problems.append("Contains characters Windows does not allow: " + " ".join(bad))
    if any(_is_control(ch) for ch in name):
        problems.append("Contains hidden control characters")
    if name in {".", ".."}:
        problems.append(f"'{name}' is not a valid folder name")
    elif name != name.rstrip(" ."):
        problems.append("Ends with a space or dot, which Windows silently removes")
    elif name != name.lstrip():
        problems.append("Starts with a space")
    if "  " in name:
        problems.append("Contains repeated spaces")
    stem = name.split(".")[0].rstrip().upper()
    if stem in RESERVED_NAMES:
        problems.append(f"'{stem}' is a reserved Windows device name")
    if len(name) > MAX_COMPONENT_LEN:
        problems.append(f"Longer than {MAX_COMPONENT_LEN} characters")
    return problems


def suggest_component(name: str) -> str:
    """Return the closest valid version of a path component ('' if nothing usable is left)."""
    text = "".join(ch for ch in name if not _is_control(ch))

    # "Title: Subtitle" reads best as "Title - Subtitle"
    text = re.sub(r"\s*:\s*$", "", text)
    text = re.sub(r"\s*:\s+", " - ", text)
    text = text.replace(":", "-")
    # "A | B" -> "A - B", "AC/DC" -> "AC-DC"
    text = re.sub(r"(\s*)[|/\\](\s*)", lambda m: " - " if (m.group(1) or m.group(2)) else "-", text)
    text = text.replace('"', "'")
    text = re.sub(r"[<>*?]", "", text)

    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"( - ){2,}", " - ", text)
    text = text.strip().rstrip(" .")

    stem = text.split(".")[0].rstrip().upper()
    if stem in RESERVED_NAMES:
        text = f"{text}_"

    if len(text) > MAX_COMPONENT_LEN:
        text = text[:MAX_COMPONENT_LEN].rstrip(" .")
    return text


def split_path(rel_path: str) -> List[str]:
    return [p for p in rel_path.replace("\\", "/").split("/")]


def analyze_name(raw: str, nested: bool = True, base_len: int = 0) -> Tuple[List[str], str]:
    """
    Check a user supplied name or relative path.

    Returns (problems, suggestion). `suggestion` is the cleaned-up path and equals
    the (normalised) input when there is nothing to fix.
    When `nested` is False, slashes are treated as ordinary text that must be
    replaced instead of being interpreted as subfolder separators.
    """
    problems: List[str] = []
    if nested:
        parts = split_path(raw.strip())
        parts = [p for p in parts if p != ""]
        if not parts:
            return ["Name is empty"], ""
        fixed = []
        for part in parts:
            for p in check_component(part, allow_separators=True):
                if p not in problems:
                    problems.append(p)
            fixed.append(suggest_component(part))
        suggestion = "/".join(fixed) if all(fixed) else ""
    else:
        part = raw.strip()
        problems = check_component(part, allow_separators=False)
        suggestion = suggest_component(part)

    if not suggestion:
        problems.append("Nothing usable is left after removing invalid characters")
        return problems, ""

    if base_len and base_len + 1 + len(suggestion) > MAX_PATH_LEN:
        allowed = max(8, MAX_PATH_LEN - base_len - 1)
        problems.append(f"Full path would exceed Windows' {MAX_PATH_LEN}-character limit")
        suggestion = suggestion[:allowed].rstrip(" .")
    return problems, suggestion
