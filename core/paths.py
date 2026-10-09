import os
import shutil
import sys


def resource_path(relative_path: str) -> str:
    """Path to a bundled resource, both from source and from a PyInstaller build."""
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return os.path.join(base, relative_path)


def startup_folder() -> str:
    """Folder the app starts in: next to the .exe when frozen, the project root otherwise."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def drive_free_space(path: str) -> str:
    try:
        target = path if os.path.exists(path) else "."
        free = shutil.disk_usage(target).free
        drive = os.path.splitdrive(os.path.abspath(target))[0] or "Drive"
        if free >= 1024 ** 4:
            return f"{drive}  {free / 1024 ** 4:.1f} TB free"
        return f"{drive}  {free / 1024 ** 3:.1f} GB free"
    except OSError:
        return ""
