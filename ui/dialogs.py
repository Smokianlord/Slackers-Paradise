import os
import subprocess
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.config import APP_NAME, APP_REPO_URL, APP_TAGLINE, APP_VERSION, config, get_config_dir
from ui import theme as T
from ui import widgets as W


class Dialog(ctk.CTkToplevel):
    """Themed, centred, modal-ish window."""

    def __init__(self, app, title: str, width: int, height: int):
        super().__init__(app, fg_color=T.BG)
        self.app = app
        self.title(title)
        self.resizable(False, False)
        self.transient(app)
        x = app.winfo_rootx() + (app.winfo_width() - width) // 2
        y = app.winfo_rooty() + max(20, (app.winfo_height() - height) // 3)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        # customtkinter re-applies its own icon shortly after creation; override it afterwards
        self.after(250, self._set_icon)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(50, self._focus)

    def _set_icon(self):
        try:
            self.iconbitmap(self.app.icon_path)
        except Exception:
            pass

    def _focus(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass


def _group(parent, title: str) -> ctk.CTkFrame:
    card = W.Card(parent)
    card.pack(fill="x", padx=22, pady=(0, 12))
    W.label(card, title, 13, T.MUTED, "semi", anchor="w").pack(anchor="w", padx=16, pady=(12, 6))
    return card


class SettingsDialog(Dialog):
    def __init__(self, app):
        super().__init__(app, "Settings", 540, 700)
        W.label(self, "Settings", 20, T.TEXT_STRONG, "semi").pack(anchor="w", padx=22, pady=(20, 14))

        # Appearance
        g = _group(self, "APPEARANCE")
        row = W.transparent(g)
        row.pack(fill="x", padx=16, pady=(0, 14))
        W.label(row, "Theme", 13).pack(side="left")
        seg = W.segmented(row, ["Dark", "Light", "System"], command=self.app.set_theme)
        seg.set(config.get("theme", "Dark"))
        seg.pack(side="right")

        # Safety
        g = _group(self, "SAFETY")
        self.confirm_var = ctk.BooleanVar(value=config.get("confirm_destructive", True))
        W.switch(g, "Ask before renaming, launching many shortcuts or cleaning", self.confirm_var,
                 lambda: config.set("confirm_destructive", self.confirm_var.get())).pack(anchor="w", padx=16, pady=(0, 10))
        self.recycle_var = ctk.BooleanVar(value=config.get("use_recycle_bin", True))
        W.switch(g, "Send cleaned folders and shortcuts to the Recycle Bin", self.recycle_var,
                 lambda: config.set("use_recycle_bin", self.recycle_var.get())).pack(anchor="w", padx=16, pady=(0, 14))

        # Folder generator
        g = _group(self, "BUILD-A-FOLDER")
        self.nested_var = ctk.BooleanVar(value=config.get("nested_paths", True))
        W.switch(g, "Treat / and \\ as sub-folder separators", self.nested_var,
                 lambda: config.set("nested_paths", self.nested_var.get())).pack(anchor="w", padx=16, pady=(0, 4))
        W.label(g, "Turn off to keep titles like \"Fate/Zero\" as one folder (becomes Fate-Zero).", 12, T.MUTED,
                anchor="w").pack(anchor="w", padx=16, pady=(0, 14))

        # Shortcut library
        g = _group(self, "SHORTCUT LIBRARY FOLDER")
        row = W.transparent(g)
        row.pack(fill="x", padx=16, pady=(0, 14))
        self.lib_entry = W.entry(row, "No folder chosen", width=300, height=34)
        self.lib_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.lib_entry.insert(0, config.get("shortcut_folder", ""))
        self.lib_entry.bind("<FocusOut>", lambda _e: self._save_library())
        W.button(row, "Browse...", self._browse_library, width=90, height=34).pack(side="right")

        # Data
        g = _group(self, "DATA")
        row = W.transparent(g)
        row.pack(fill="x", padx=16, pady=(0, 14))
        W.button(row, "Open settings folder", lambda: os.startfile(get_config_dir()), width=170, height=34).pack(side="left")
        W.button(row, "Reset all settings", self._reset, kind="ghost", width=150, height=34).pack(side="left", padx=8)

        W.button(self, "Done", self.destroy, kind="primary", width=110).pack(side="right", padx=22, pady=(4, 18))

    def _save_library(self):
        value = self.lib_entry.get().strip().strip('"')
        if value and os.path.isdir(value):
            config.set("shortcut_folder", os.path.abspath(value))

    def _browse_library(self):
        chosen = filedialog.askdirectory(parent=self, initialdir=self.lib_entry.get() or None)
        if chosen:
            self.lib_entry.delete(0, "end")
            self.lib_entry.insert(0, os.path.abspath(chosen))
            self._save_library()

    def _reset(self):
        if messagebox.askyesno("Reset settings", "Restore every setting to its default?\n(Your saved templates are removed too.)", parent=self):
            config.reset()
            self.app.set_theme(config.get("theme"))
            self.destroy()
            self.app.notify("Settings were reset.", "success")


GUIDE = [
    ("Build-a-Folder", "Type or paste one folder name per line. Commas, apostrophes and punctuation are kept - "
     "only characters Windows forbids (: ? \" * | < > and trailing dots) are flagged. Each flagged line shows a suggested "
     "fix (for example 'Title: Subtitle' becomes 'Title - Subtitle'). Use sequences like Episode_{01..12} for numbered sets."),
    ("FolderFolio", "Scan a folder and export the result as a list, ASCII tree, CSV, Markdown or JSON. The filter box "
     "narrows both the table and what you export."),
    ("RenameRoulette", "Pick a mode, review the live preview, then rename. Conflicts and invalid names are never applied, "
     "and the whole batch can be undone."),
    ("ShortcutExecutor", "Launch many shortcuts with a delay between each one so your PC stays responsive. "
     "Click the checkbox column to choose, double-click a row to launch just that one."),
    ("SlackerCleaner", "Scan for old temp files, empty folders and broken shortcuts. Review the list, untick anything "
     "you want to keep, then clean. Folders and shortcuts go to the Recycle Bin."),
]
KEYS = [
    ("Ctrl + 1 ... 5", "Switch tool"),
    ("Ctrl + O", "Choose working folder"),
    ("Ctrl + L", "Show / hide activity log"),
    ("Ctrl + ,", "Settings"),
    ("F1", "Help"),
    ("Esc", "Close dialogs"),
]


class HelpDialog(Dialog):
    def __init__(self, app):
        super().__init__(app, f"About {APP_NAME}", 620, 640)
        head = W.transparent(self)
        head.pack(fill="x", padx=24, pady=(22, 6))
        W.label(head, APP_NAME, 22, T.TEXT_STRONG, "semi").pack(anchor="w")
        W.label(head, f"Version {APP_VERSION}  ·  {APP_TAGLINE}", 13, T.MUTED).pack(anchor="w", pady=(2, 0))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=T.BORDER,
                                        scrollbar_button_hover_color=T.FAINT)
        scroll.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        g = _group(scroll, "TOOLS")
        for name, text in GUIDE:
            W.label(g, name, 13, T.TEXT_STRONG, "semi", anchor="w").pack(anchor="w", padx=16, pady=(4, 0))
            W.label(g, text, 12, T.MUTED, anchor="w", justify="left", wraplength=520).pack(anchor="w", padx=16, pady=(0, 8))

        g = _group(scroll, "KEYBOARD SHORTCUTS")
        for keys, what in KEYS:
            r = W.transparent(g)
            r.pack(fill="x", padx=16, pady=2)
            W.label(r, keys, 13, T.ACCENT, "semi", width=120, anchor="w").pack(side="left")
            W.label(r, what, 13, T.TEXT).pack(side="left")
        W.transparent(g, height=8).pack()

        row = W.transparent(self)
        row.pack(fill="x", padx=24, pady=14)
        W.button(row, "Project page", lambda: os.startfile(APP_REPO_URL), kind="secondary", width=120).pack(side="left")
        W.button(row, "Close", self.destroy, kind="primary", width=100).pack(side="right")
