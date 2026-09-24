import os
import sys
import json
from pathlib import Path

APP_NAME = "Slackers-Paradise"
APP_VERSION = "3.0.0"

DEFAULT_CONFIG = {
    "theme": "Dark",
    "color_theme": "blue",
    "default_gaming_folder": r"D:\Gaming Shortcuts" if os.path.exists(r"D:\Gaming Shortcuts") else str(Path.home() / "Desktop"),
    "recent_folders": [],
    "shortcut_delay_ms": 500,
    "confirm_destructive": True,
    "auto_open_after_create": False,
    "custom_templates": {
        "Web Project": [
            "src",
            "src/components",
            "src/assets/images",
            "src/assets/styles",
            "src/utils",
            "public",
            "tests",
            "docs"
        ],
        "Python App": [
            "src",
            "src/core",
            "src/ui",
            "tests",
            "docs",
            "scripts",
            "config"
        ],
        "Media Creator": [
            "01_RAW_Footage",
            "02_Audio_BGM",
            "03_Graphics_VFX",
            "04_Draft_Edits",
            "05_Final_Exports",
            "06_Thumbnails"
        ],
        "University / School": [
            "01_Lectures",
            "02_Assignments",
            "03_Readings",
            "04_Notes",
            "05_Submissions"
        ],
        "Yearly Months": [
            f"{i:02d}_{month}" for i, month in enumerate([
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ], start=1)
        ]
    }
}


def get_config_dir() -> Path:
    if os.name == "nt":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data) / "SlackersParadise"
            base.mkdir(parents=True, exist_ok=True)
            return base
    base = Path.home() / ".slackers_paradise"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


class ConfigManager:
    def __init__(self):
        self.path = get_config_path()
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def add_recent_folder(self, folder: str):
        if not folder or not os.path.isdir(folder):
            return
        folder = os.path.abspath(folder)
        recents = [f for f in self.data.get("recent_folders", []) if f.lower() != folder.lower()]
        recents.insert(0, folder)
        self.data["recent_folders"] = recents[:10]
        self.save()

    def get_recent_folders(self):
        return [f for f in self.data.get("recent_folders", []) if os.path.isdir(f)]


# Global instance
config = ConfigManager()
