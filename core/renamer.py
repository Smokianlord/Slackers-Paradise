import os
import uuid
import random
import string
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any


class RenameEngine:
    def __init__(self):
        self.undo_stack: List[List[Tuple[Path, Path]]] = []

    def generate_plan(
        self,
        folder: Path,
        mode: str = "roulette",
        # Roulette params:
        random_type: str = "4_digit",  # 4_digit, 6_digit, 8_digit, hex, alphanumeric, uuid
        # Sequential params:
        seq_prefix: str = "Item_",
        seq_start: int = 1,
        seq_padding: int = 3,
        seq_suffix: str = "",
        # Find/replace params:
        find_text: str = "",
        replace_text: str = "",
        add_prefix: str = "",
        add_suffix: str = "",
        # Case transform:
        case_mode: str = "lower",  # lower, upper, title, snake, kebab
        # Filter params:
        extension_filter: str = "*",
        include_hidden: bool = False
    ) -> Dict[str, Any]:
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid directory: {folder}")

        # Gather files
        entries = sorted([p for p in folder.iterdir() if p.is_file()], key=lambda p: p.name.lower())
        
        # Filter extensions
        ext_list = [e.strip().lower() for e in extension_filter.split(";") if e.strip()]
        if not ext_list or "*" in ext_list or "*.*" in ext_list:
            files = entries
        else:
            files = [
                f for f in entries
                if any(f.suffix.lower() == ext or (not ext.startswith(".") and f.suffix.lower() == f".{ext}") for ext in ext_list)
            ]

        if not include_hidden:
            files = [f for f in files if not f.name.startswith(".")]

        plan = []
        used_new_names = set()
        existing_on_disk = {p.name.lower() for p in folder.iterdir()}

        for idx, src in enumerate(files):
            stem = src.stem
            ext = src.suffix
            new_name = src.name

            if mode == "roulette":
                new_name = self._make_random_name(random_type, ext, used_new_names, existing_on_disk, src.name)
            elif mode == "sequential":
                num_str = f"{seq_start + idx:0{seq_padding}d}"
                new_name = f"{seq_prefix}{num_str}{seq_suffix}{ext}"
            elif mode == "find_replace":
                new_stem = stem
                if find_text:
                    new_stem = new_stem.replace(find_text, replace_text)
                new_stem = f"{add_prefix}{new_stem}{add_suffix}"
                new_name = f"{new_stem}{ext}"
            elif mode == "date_stamp":
                try:
                    mtime = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d")
                except Exception:
                    mtime = datetime.now().strftime("%Y-%m-%d")
                new_name = f"{mtime}_{stem}{ext}"
            elif mode == "case":
                if case_mode == "lower":
                    new_name = f"{stem.lower()}{ext.lower()}"
                elif case_mode == "upper":
                    new_name = f"{stem.upper()}{ext.lower()}"
                elif case_mode == "title":
                    new_name = f"{stem.title()}{ext.lower()}"
                elif case_mode == "snake":
                    clean = re.sub(r"[\s\-]+", "_", stem)
                    new_name = f"{clean.lower()}{ext.lower()}"
                elif case_mode == "kebab":
                    clean = re.sub(r"[\s\_]+", "-", stem)
                    new_name = f"{clean.lower()}{ext.lower()}"

            # Check status
            if new_name == src.name:
                status = "unchanged"
                msg = "No change"
            elif new_name.lower() in used_new_names:
                status = "conflict"
                msg = "Duplicate target name in batch"
            elif new_name.lower() in existing_on_disk and (folder / new_name) not in files:
                status = "conflict"
                msg = "Conflicts with existing file on disk"
            else:
                status = "ready"
                msg = "Ready to rename"

            used_new_names.add(new_name.lower())
            plan.append({
                "source": src,
                "old_name": src.name,
                "new_name": new_name,
                "destination": folder / new_name,
                "status": status,
                "message": msg
            })

        conflicts = sum(1 for item in plan if item["status"] == "conflict")
        ready = sum(1 for item in plan if item["status"] == "ready")
        unchanged = sum(1 for item in plan if item["status"] == "unchanged")

        return {
            "folder": folder,
            "items": plan,
            "total": len(plan),
            "ready": ready,
            "conflicts": conflicts,
            "unchanged": unchanged
        }

    def _make_random_name(self, rtype: str, ext: str, used: set, disk_names: set, current_name: str) -> str:
        for _ in range(50000):
            if rtype == "4_digit":
                rand_part = str(random.randint(1000, 9999))
            elif rtype == "6_digit":
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
            cand_low = candidate.lower()
            if cand_low not in used and (cand_low not in disk_names or candidate == current_name):
                return candidate
        return f"{uuid.uuid4().hex[:8]}{ext}"

    def execute_rename(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        items_to_rename = [it for it in plan_data["items"] if it["status"] == "ready"]
        if not items_to_rename:
            return {"renamed": 0, "failed": [], "can_undo": bool(self.undo_stack)}

        folder = plan_data["folder"]
        # Safe two-phase rename with temporary UUIDs
        temp_mappings = []
        final_mappings = []
        successful_records = []
        failed = []

        try:
            # Phase 1: Rename to temporary names to avoid chain collisions
            for item in items_to_rename:
                src = item["source"]
                tmp_name = f".tmp_sp_{uuid.uuid4().hex[:12]}{src.suffix}"
                tmp_path = folder / tmp_name
                try:
                    src.rename(tmp_path)
                    temp_mappings.append((src, tmp_path, item["destination"], item["new_name"]))
                except Exception as exc:
                    failed.append((item["old_name"], f"Phase 1 error: {exc}"))

            # Phase 2: Rename from temporary names to final names
            for original_src, tmp_path, dst, new_name in temp_mappings:
                try:
                    tmp_path.rename(dst)
                    successful_records.append((original_src, dst))
                except Exception as exc:
                    # Try to restore back to original name if final rename fails
                    try:
                        tmp_path.rename(original_src)
                    except Exception:
                        pass
                    failed.append((original_src.name, f"Phase 2 error: {exc}"))

        except Exception as exc:
            failed.append(("Global error", str(exc)))

        if successful_records:
            # Store in undo stack: (destination_now, original_source)
            self.undo_stack.append([(dst, orig) for orig, dst in successful_records])

        return {
            "renamed": len(successful_records),
            "failed": failed,
            "can_undo": bool(self.undo_stack)
        }

    def undo_last_rename(self) -> Dict[str, Any]:
        if not self.undo_stack:
            return {"restored": 0, "failed": ["No rename actions available to undo."]}

        transaction = self.undo_stack.pop()
        restored = 0
        failed = []

        for current_path, original_path in transaction:
            try:
                if current_path.exists():
                    current_path.rename(original_path)
                    restored += 1
                else:
                    failed.append((current_path.name, "File no longer exists at expected path"))
            except Exception as exc:
                failed.append((current_path.name, str(exc)))

        return {
            "restored": restored,
            "failed": failed,
            "remaining_undo": len(self.undo_stack)
        }


# Global instance
renamer_engine = RenameEngine()
