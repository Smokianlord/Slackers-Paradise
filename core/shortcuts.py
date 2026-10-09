import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SUPPORTED_EXTS = {".lnk", ".url", ".bat", ".cmd", ".exe"}

_com_state = threading.local()


def _get_wscript_shell():
    """One WScript.Shell per thread (COM must be initialised on every thread that uses it)."""
    shell = getattr(_com_state, "shell", None)
    if shell is None:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        _com_state.shell = shell
    return shell


def resolve_lnk_target(lnk_path: Path) -> Dict[str, Any]:
    """`resolved` is False when the target could not be read (pywin32 missing, corrupt file...)."""
    target, arguments, valid, resolved = "", "", True, False
    try:
        shortcut = _get_wscript_shell().CreateShortcut(str(lnk_path))
        target = shortcut.TargetPath
        arguments = shortcut.Arguments
        resolved = True
        # A shortcut without a path (e.g. to a Control Panel item) is not "broken"
        valid = os.path.exists(target) if target else True
    except Exception:
        target = ""
    return {"target": target, "arguments": arguments, "valid": valid, "resolved": resolved}


def resolve_url_target(url_path: Path) -> str:
    try:
        for line in url_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().lower().startswith("url="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def scan_shortcuts(folder: Path) -> List[Dict[str, Any]]:
    if not folder.is_dir():
        return []
    try:
        entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []

    items = []
    for entry in entries:
        ext = entry.suffix.lower()
        if ext not in SUPPORTED_EXTS or not entry.is_file():
            continue
        info = {"target": "", "arguments": "", "valid": True}
        if ext == ".lnk":
            info = resolve_lnk_target(entry)
            if not info["target"]:
                info["target"] = "(system shortcut)" if info["resolved"] else str(entry)
        elif ext == ".url":
            info["target"] = resolve_url_target(entry)
        else:
            info["target"] = str(entry)

        items.append({
            "path": entry,
            "name": entry.stem,
            "filename": entry.name,
            "extension": ext,
            "type": ext[1:].upper(),
            "target": info["target"],
            "arguments": info.get("arguments", ""),
            "is_valid": info.get("valid", True),
            "selected": True,
        })
    return items


class ShortcutRunner:
    def __init__(self):
        self.is_running = False
        self.abort_requested = False
        self.worker_thread: Optional[threading.Thread] = None

    def launch_staggered(
        self,
        shortcuts: List[Dict[str, Any]],
        delay_ms: int = 500,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_complete: Optional[Callable[[int, List[Tuple[str, str]], bool], None]] = None,
    ) -> bool:
        if self.is_running:
            return False
        self.is_running = True
        self.abort_requested = False
        delay_sec = max(0, delay_ms) / 1000.0

        def task():
            launched = 0
            failed: List[Tuple[str, str]] = []
            total = len(shortcuts)
            try:
                for i, sc in enumerate(shortcuts, start=1):
                    if self.abort_requested:
                        break
                    if on_progress:
                        on_progress(i, total, sc["name"])
                    try:
                        if os.name == "nt":
                            os.startfile(str(sc["path"]))
                        else:
                            import subprocess
                            subprocess.Popen(["xdg-open", str(sc["path"])])
                        launched += 1
                    except Exception as exc:
                        failed.append((sc["filename"], str(exc)))
                    # Sleep in small slices so Abort reacts immediately
                    deadline = time.time() + delay_sec
                    while i < total and time.time() < deadline and not self.abort_requested:
                        time.sleep(0.05)
            finally:
                self.is_running = False
                if on_complete:
                    on_complete(launched, failed, self.abort_requested)

        self.worker_thread = threading.Thread(target=task, daemon=True)
        self.worker_thread.start()
        return True

    def abort(self):
        self.abort_requested = True


# Global instance
shortcut_runner = ShortcutRunner()
