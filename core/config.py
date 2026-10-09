import copy
import json
import os
from pathlib import Path

APP_NAME = "Slackers-Paradise"
APP_VERSION = "4.0.0"
APP_TAGLINE = "Folder & file automation for Windows"
APP_REPO_URL = "https://github.com/Smokianlord/Slackers-Paradise"

BUILTIN_TEMPLATES = {
    "Web Project": [
        "src", "src/components", "src/assets/images", "src/assets/styles",
        "src/utils", "public", "tests", "docs",
    ],
    "Python App": ["src", "src/core", "src/ui", "tests", "docs", "scripts", "config"],
    "Media Creator": [
        "01_RAW_Footage", "02_Audio_BGM", "03_Graphics_VFX",
        "04_Draft_Edits", "05_Final_Exports", "06_Thumbnails",
    ],
    "University / School": ["01_Lectures", "02_Assignments", "03_Readings", "04_Notes", "05_Submissions"],
    "Yearly Months": [
        f"{i:02d}_{month}" for i, month in enumerate([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ], start=1)
    ],
}

DEFAULT_CONFIG = {
    "theme": "Dark",                      # Dark | Light | System
    "shortcut_folder": str(Path.home() / "Desktop"),
    "recent_folders": [],
    "last_folder": "",
    "last_view": "build",
    "window_geometry": "",
    "shortcut_delay_ms": 500,
    "confirm_destructive": True,
    "use_recycle_bin": True,              # cleaner sends non-temp items to the Recycle Bin
    "auto_open_after_create": False,
    "nested_paths": True,                 # "/" in a line creates sub-folders
    "custom_templates": {},               # user templates, merged with BUILTIN_TEMPLATES
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
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if not self.path.exists():
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            return
        if not isinstance(loaded, dict):
            return
        # Migrate settings from v3
        if "default_gaming_folder" in loaded and "shortcut_folder" not in loaded:
            legacy = loaded["default_gaming_folder"]
            if legacy and os.path.isdir(legacy):
                loaded["shortcut_folder"] = legacy
        if not isinstance(loaded.get("custom_templates"), dict) or "Web Project" in loaded.get("custom_templates", {}):
            loaded["custom_templates"] = {}
        if loaded.get("theme") not in ("Dark", "Light", "System"):
            loaded["theme"] = "Dark"
        self.data.update({k: v for k, v in loaded.items() if k in DEFAULT_CONFIG})

    def save(self):
        try:
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def reset(self):
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self.save()

    # -- recent folders -------------------------------------------------
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

    # -- templates --------------------------------------------------------
    def all_templates(self):
        merged = copy.deepcopy(BUILTIN_TEMPLATES)
        merged.update(self.data.get("custom_templates", {}))
        return merged

    def save_template(self, name: str, lines):
        tpls = dict(self.data.get("custom_templates", {}))
        tpls[name] = list(lines)
        self.set("custom_templates", tpls)

    def delete_template(self, name: str) -> bool:
        tpls = dict(self.data.get("custom_templates", {}))
        if name in tpls:
            del tpls[name]
            self.set("custom_templates", tpls)
            return True
        return False

    def is_builtin_template(self, name: str) -> bool:
        return name in BUILTIN_TEMPLATES and name not in self.data.get("custom_templates", {})


# Global instance
config = ConfigManager()
