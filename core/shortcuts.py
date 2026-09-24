import os
import sys
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple


def resolve_lnk_target(lnk_path: Path) -> Dict[str, Any]:
    target = ""
    arguments = ""
    valid = True

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(lnk_path))
        target = shortcut.TargetPath
        arguments = shortcut.Arguments
        if target:
            valid = os.path.exists(target)
    except Exception:
        # Fallback if win32com is unavailable
        target = str(lnk_path)
        valid = True

    return {
        "target": target,
        "arguments": arguments,
        "valid": valid
    }


def resolve_url_target(url_path: Path) -> str:
    try:
        lines = url_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines:
            if line.strip().lower().startswith("url="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def scan_shortcuts(folder: Path) -> List[Dict[str, Any]]:
    if not folder.exists() or not folder.is_dir():
        return []

    supported_exts = {".lnk", ".url", ".bat", ".cmd", ".exe"}
    items = []

    try:
        entries = sorted(list(folder.iterdir()), key=lambda p: p.name.lower())
    except Exception:
        return []

    for entry in entries:
        ext = entry.suffix.lower()
        if ext in supported_exts and entry.is_file():
            target_info = {"target": "", "arguments": "", "valid": True}
            if ext == ".lnk":
                target_info = resolve_lnk_target(entry)
            elif ext == ".url":
                target_info["target"] = resolve_url_target(entry)
            else:
                target_info["target"] = str(entry)

            items.append({
                "path": entry,
                "name": entry.stem,
                "filename": entry.name,
                "extension": ext,
                "type": ext[1:].upper(),
                "target": target_info["target"],
                "arguments": target_info.get("arguments", ""),
                "is_valid": target_info.get("valid", True),
                "selected": True
            })

    return items


class ShortcutRunner:
    def __init__(self):
        self.is_running = False
        self.abort_requested = False
        self.worker_thread = None

    def launch_staggered(
        self,
        shortcuts: List[Dict[str, Any]],
        delay_ms: int = 500,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_complete: Optional[Callable[[int, List[Tuple[str, str]]], None]] = None
    ):
        if self.is_running:
            return False

        self.is_running = True
        self.abort_requested = False

        def task():
            launched = 0
            failed = []
            total = len(shortcuts)
            delay_sec = max(0, delay_ms / 1000.0)

            for i, sc in enumerate(shortcuts, start=1):
                if self.abort_requested:
                    break

                sc_path = sc["path"]
                if on_progress:
                    on_progress(i, total, sc["name"])

                try:
                    if os.name == "nt":
                        os.startfile(str(sc_path))
                    else:
                        import subprocess
                        subprocess.Popen(["xdg-open", str(sc_path)])
                    launched += 1
                except Exception as exc:
                    failed.append((sc["filename"], str(exc)))

                if i < total and delay_sec > 0 and not self.abort_requested:
                    time.sleep(delay_sec)

            self.is_running = False
            if on_complete:
                on_complete(launched, failed)

        self.worker_thread = threading.Thread(target=task, daemon=True)
        self.worker_thread.start()
        return True

    def abort(self):
        self.abort_requested = True


# Global instance
shortcut_runner = ShortcutRunner()
