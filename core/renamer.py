import random
import re
import string
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.folio import is_hidden_or_system
from core.naming import check_component

DATE_FORMATS = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYYMMDD": "%Y%m%d",
    "YYYY-MM-DD_HHMM": "%Y-%m-%d_%H%M",
    "DD-MM-YYYY": "%d-%m-%Y",
}


def natural_key(text: str):
    """Sort key so that 'file2' comes before 'file10'."""
    return [int(tok) if tok.isdigit() else tok.lower() for tok in re.split(r"(\d+)", text)]


def _match_extension(path: Path, ext_list: List[str]) -> bool:
    suffix = path.suffix.lower()
    for ext in ext_list:
        ext = ext.lstrip("*")
        if not ext.startswith("."):
            ext = f".{ext}"
        if suffix == ext:
            return True
    return False


class RenameEngine:
    def __init__(self):
        self.undo_stack: List[List[Tuple[Path, Path]]] = []

    # ------------------------------------------------------------------ plan
    def generate_plan(
        self,
        folder: Path,
        mode: str = "roulette",
        random_type: str = "4_digit",     # 4_digit, 6_digit, 8_digit, hex, alphanumeric, uuid
        seq_prefix: str = "Item_",
        seq_start: int = 1,
        seq_padding: int = 3,
        seq_suffix: str = "",
        find_text: str = "",
        replace_text: str = "",
        add_prefix: str = "",
        add_suffix: str = "",
        case_sensitive: bool = True,
        use_regex: bool = False,
        date_source: str = "today",
        date_format: str = "YYYY-MM-DD",
        date_placement: str = "prefix",
        case_mode: str = "lower",         # lower, upper, title, snake, kebab
        extension_filter: str = "*",
        include_hidden: bool = False,
        sort_by: str = "name",            # name, modified, size
    ) -> Dict[str, Any]:
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid directory: {folder}")

        regex = None
        if mode == "find_replace" and find_text and use_regex:
            try:
                regex = re.compile(find_text, 0 if case_sensitive else re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"Invalid regular expression: {exc}")

        all_entries = list(folder.iterdir())
        entries = [p for p in all_entries if p.is_file()]

        ext_list = [e.strip().lower() for e in extension_filter.split(";") if e.strip()]
        if ext_list and "*" not in ext_list and "*.*" not in ext_list:
            entries = [f for f in entries if _match_extension(f, ext_list)]
        if not include_hidden:
            entries = [f for f in entries if not is_hidden_or_system(f)]

        def safe_stat(p: Path, attr: str):
            try:
                return getattr(p.stat(), attr)
            except OSError:
                return 0

        if sort_by == "modified":
            entries.sort(key=lambda p: (safe_stat(p, "st_mtime"), natural_key(p.name)))
        elif sort_by == "size":
            entries.sort(key=lambda p: (safe_stat(p, "st_size"), natural_key(p.name)))
        else:
            entries.sort(key=lambda p: natural_key(p.name))
        files = entries

        plan = []
        used_new_names = set()
        batch_names = {f.name.lower() for f in files}
        other_names_on_disk = {p.name.lower() for p in all_entries} - batch_names

        for idx, src in enumerate(files):
            stem, ext = src.stem, src.suffix
            new_name = src.name

            if mode == "roulette":
                new_name = self._make_random_name(
                    random_type, ext, used_new_names | other_names_on_disk, src.name
                )
            elif mode == "sequential":
                new_name = f"{seq_prefix}{seq_start + idx:0{max(1, seq_padding)}d}{seq_suffix}{ext}"
            elif mode == "find_replace":
                new_stem = stem
                if find_text:
                    if regex is not None:
                        try:
                            new_stem = regex.sub(replace_text, new_stem)
                        except (re.error, IndexError) as exc:
                            raise ValueError(f"Invalid replacement pattern: {exc}")
                    elif case_sensitive:
                        new_stem = new_stem.replace(find_text, replace_text)
                    else:
                        new_stem = re.sub(re.escape(find_text), lambda _m: replace_text, new_stem, flags=re.IGNORECASE)
                new_name = f"{add_prefix}{new_stem}{add_suffix}{ext}"
            elif mode == "date_stamp":
                fmt = DATE_FORMATS.get(date_format, date_format if "%" in date_format else "%Y-%m-%d")
                if date_source == "today":
                    stamp = datetime.now().strftime(fmt)
                else:
                    try:
                        stamp = datetime.fromtimestamp(src.stat().st_mtime).strftime(fmt)
                    except OSError:
                        stamp = datetime.now().strftime(fmt)
                new_name = f"{stem}_{stamp}{ext}" if date_placement == "suffix" else f"{stamp}_{stem}{ext}"
            elif mode == "case":
                if case_mode == "lower":
                    new_name = f"{stem.lower()}{ext.lower()}"
                elif case_mode == "upper":
                    new_name = f"{stem.upper()}{ext.lower()}"
                elif case_mode == "title":
                    new_name = f"{stem.title()}{ext.lower()}"
                elif case_mode == "snake":
                    snake = re.sub(r"[\s\-]+", "_", stem).lower()
                    new_name = f"{snake}{ext.lower()}"
                elif case_mode == "kebab":
                    kebab = re.sub(r"[\s_]+", "-", stem).lower()
                    new_name = f"{kebab}{ext.lower()}"

            problems = check_component(new_name) if new_name != src.name else []
            low = new_name.lower()
            if new_name == src.name:
                status, msg = "unchanged", "No change"
            elif problems:
                status, msg = "invalid", problems[0]
            elif low in used_new_names:
                status, msg = "conflict", "Another file in this batch gets the same name"
            elif low in other_names_on_disk:
                status, msg = "conflict", "A different file with this name already exists"
            else:
                status, msg = "ready", "Ready to rename"

            used_new_names.add(low)
            plan.append({
                "source": src,
                "old_name": src.name,
                "new_name": new_name,
                "destination": folder / new_name,
                "status": status,
                "message": msg,
            })

        return {
            "folder": folder,
            "items": plan,
            "total": len(plan),
            "ready": sum(1 for it in plan if it["status"] == "ready"),
            "conflicts": sum(1 for it in plan if it["status"] == "conflict"),
            "invalid": sum(1 for it in plan if it["status"] == "invalid"),
            "unchanged": sum(1 for it in plan if it["status"] == "unchanged"),
        }

    def _make_random_name(self, rtype: str, ext: str, taken: set, current_name: str) -> str:
        for _ in range(5000):
            if rtype == "6_digit":
                rand_part = str(random.randint(100000, 999999))
            elif rtype == "8_digit":
                rand_part = str(random.randint(10000000, 99999999))
            elif rtype == "hex":
                rand_part = "".join(random.choices("0123456789abcdef", k=6))
            elif rtype == "alphanumeric":
                rand_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
            elif rtype == "uuid":
                rand_part = str(uuid.uuid4())[:8]
            else:
                rand_part = str(random.randint(1000, 9999))
            candidate = f"{rand_part}{ext}"
            if candidate.lower() not in taken:
                return candidate
        return f"{uuid.uuid4().hex[:12]}{ext}"

    # --------------------------------------------------------------- execute
    @staticmethod
    def _two_phase(pairs: List[Tuple[Path, Path]]):
        """
        Rename (src -> dst) pairs without chain collisions (a->b, b->c, swaps...).
        Returns (done_pairs, failed) where failed is a list of (name, reason).
        """
        staged: List[Tuple[Path, Path, Path]] = []
        failed: List[Tuple[str, str]] = []
        done: List[Tuple[Path, Path]] = []

        for src, dst in pairs:
            tmp = src.with_name(f".tmp_sp_{uuid.uuid4().hex[:12]}{src.suffix}")
            try:
                src.rename(tmp)
                staged.append((src, tmp, dst))
            except OSError as exc:
                failed.append((src.name, f"Could not start rename: {exc}"))

        for src, tmp, dst in staged:
            try:
                tmp.rename(dst)
                done.append((src, dst))
            except OSError as exc:
                try:
                    tmp.rename(src)  # put the original back
                except OSError:
                    failed.append((src.name, f"Left as {tmp.name}: {exc}"))
                    continue
                failed.append((src.name, str(exc)))
        return done, failed

    def execute_rename(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        items = [it for it in plan_data["items"] if it["status"] == "ready"]
        if not items:
            return {"renamed": 0, "failed": [], "can_undo": bool(self.undo_stack)}

        done, failed = self._two_phase([(it["source"], it["destination"]) for it in items])
        if done:
            self.undo_stack.append([(dst, orig) for orig, dst in done])
        return {"renamed": len(done), "failed": failed, "can_undo": bool(self.undo_stack)}

    def undo_last_rename(self) -> Dict[str, Any]:
        if not self.undo_stack:
            return {"restored": 0, "failed": ["Nothing to undo."], "remaining_undo": 0}

        transaction = self.undo_stack.pop()
        pairs, failed = [], []
        for current, original in transaction:
            if current.exists():
                pairs.append((current, original))
            else:
                failed.append((current.name, "File is no longer at its renamed location"))

        done, more_failed = self._two_phase(pairs)
        return {"restored": len(done), "failed": failed + more_failed, "remaining_undo": len(self.undo_stack)}


# Global instance
renamer_engine = RenameEngine()
