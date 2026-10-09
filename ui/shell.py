import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from core.config import APP_NAME, APP_VERSION, config
from core.paths import drive_free_space, resource_path, startup_folder
from ui import theme as T
from ui import widgets as W
from ui.dialogs import HelpDialog, SettingsDialog
from ui.views.build import BuildFolderView
from ui.views.cleaner import SlackerCleanerView
from ui.views.folio import FolderFolioView
from ui.views.rename import RenameRouletteView
from ui.views.shortcuts import ShortcutExecutorView

VIEWS = [
    # key, class, nav label, icon
    ("build", BuildFolderView, "Build-a-Folder", "build"),
    ("folio", FolderFolioView, "FolderFolio", "folio"),
    ("rename", RenameRouletteView, "RenameRoulette", "rename"),
    ("shortcuts", ShortcutExecutorView, "ShortcutExecutor", "shortcuts"),
    ("cleaner", SlackerCleanerView, "SlackerCleaner", "cleaner"),
]
VIEW_CLASSES = {key: cls for key, cls, _l, _i in VIEWS}


class SlackersParadiseApp(ctk.CTk):
    def __init__(self):
        mode = config.get("theme", "Dark")
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=T.BG)

        self.title(APP_NAME)
        self._apply_geometry()
        self.minsize(1080, 700)
        self.icon_path = resource_path(os.path.join("assets", "app.ico"))
        try:
            self.iconbitmap(self.icon_path)
        except Exception:
            pass

        last = config.get("last_folder", "")
        self.active_folder_var = tk.StringVar(value=last if last and os.path.isdir(last) else startup_folder())
        config.add_recent_folder(self.active_folder_var.get())

        self.views = {}
        self._instances = []
        self.detached = {}
        self.current_key = None
        self._busy_count = 0

        T.apply_ttk_style(self)
        self._build_sidebar()
        self._build_main()
        self.toasts = W.ToastHost(self.main, bottom_offset=44)
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        start = config.get("last_view", "build")
        self.show_view(start if start in VIEW_CLASSES else "build")
        self.log(f"{APP_NAME} {APP_VERSION} ready.", "success")

    # ------------------------------------------------------------------ layout
    def _apply_geometry(self):
        saved = config.get("window_geometry", "")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        if saved:
            self.geometry(saved)
            return
        w, h = min(1320, sw - 80), min(860, sh - 100)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(10, (sh - h) // 3)}")

    def _build_sidebar(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=240, fg_color=T.SIDEBAR, corner_radius=0,
                            border_width=0)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        side.pack_propagate(False)
        ctk.CTkFrame(self, width=1, fg_color=T.BORDER, corner_radius=0).grid(row=0, column=0, sticky="nse")

        brand = W.transparent(side)
        brand.pack(fill="x", padx=18, pady=(22, 22))
        png = resource_path(os.path.join("assets", "app.png"))
        try:
            img = Image.open(png)
            logo = ctk.CTkImage(light_image=img, dark_image=img, size=(34, 34))
            ctk.CTkLabel(brand, image=logo, text="").pack(side="left", padx=(0, 10))
        except Exception:
            pass
        names = W.transparent(brand)
        names.pack(side="left")
        W.label(names, APP_NAME, 15, T.TEXT_STRONG, "semi", anchor="w").pack(anchor="w")
        W.label(names, f"Version {APP_VERSION}", 11, T.MUTED, anchor="w").pack(anchor="w")

        W.label(side, "TOOLS", 10, T.FAINT, "semi", anchor="w").pack(anchor="w", padx=24, pady=(0, 6))
        self.nav = {}
        holder = W.transparent(side)
        holder.pack(fill="x", padx=12)
        for i, (key, _cls, text, icon_name) in enumerate(VIEWS, start=1):
            item = W.NavItem(holder, icon_name, text, f"Ctrl+{i}", command=lambda k=key: self.show_view(k))
            item.pack(fill="x", pady=2)
            self.nav[key] = item

        bottom = W.transparent(side)
        bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 14))
        W.NavItem(bottom, "theme", "Switch theme", command=self.toggle_theme).pack(fill="x", pady=2)
        W.NavItem(bottom, "settings", "Settings", "Ctrl+,", command=self.open_settings).pack(fill="x", pady=2)
        W.NavItem(bottom, "help", "Help & About", "F1", command=self.open_help).pack(fill="x", pady=2)
        W.divider(side).pack(side="bottom", fill="x", padx=18, pady=(0, 10))

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")

        # Working folder bar
        bar = ctk.CTkFrame(self.main, fg_color=T.SURFACE, corner_radius=0, height=64)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        ctk.CTkFrame(self.main, height=1, fg_color=T.BORDER, corner_radius=0).pack(fill="x", side="top")
        inner = W.transparent(bar)
        inner.pack(fill="both", expand=True, padx=24, pady=14)
        W.label(inner, "WORKING FOLDER", 10, T.FAINT, "semi").pack(side="left", padx=(0, 12))
        self.dir_entry = ctk.CTkEntry(inner, textvariable=self.active_folder_var, height=36, corner_radius=T.RADIUS_SM,
                                      fg_color=T.SURFACE_ALT, border_color=T.BORDER, border_width=1,
                                      text_color=T.TEXT, font=T.mono(12))
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.dir_entry.bind("<Return>", lambda _e: self._on_dir_typed())
        self.dir_entry.bind("<FocusOut>", lambda _e: self.active_folder_var.set(self.get_active_folder()))
        W.button(inner, "Browse", self.browse_folder, kind="primary", width=88, height=36).pack(side="left", padx=(0, 6))
        W.button(inner, "Explorer", self.open_current_in_explorer, kind="secondary", width=86, height=36).pack(side="left", padx=(0, 6))
        W.button(inner, "Terminal", self.open_current_in_terminal, kind="secondary", width=86, height=36).pack(side="left", padx=(0, 6))
        self.recent_menu = W.option_menu(inner, ["Recent"], width=100, height=36, command=self._on_recent)
        self.recent_menu.pack(side="left")
        self._refresh_recent_menu()

        # Status bar + log drawer (packed bottom-up before the workspace fills the rest)
        self.status_bar = ctk.CTkFrame(self.main, height=30, fg_color=T.SIDEBAR, corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        ctk.CTkFrame(self.main, height=1, fg_color=T.BORDER, corner_radius=0).pack(side="bottom", fill="x")
        sb = W.transparent(self.status_bar)
        sb.pack(fill="both", expand=True, padx=20)
        self.status_dot = ctk.CTkLabel(sb, text="●", font=T.font(10), text_color=T.SUCCESS, width=14)
        self.status_dot.pack(side="left")
        self.status_lbl = W.label(sb, "Ready", 12, T.MUTED, anchor="w")
        self.status_lbl.pack(side="left", padx=(4, 0))
        self.log_toggle = W.button(sb, "Activity log", self.toggle_log_drawer, kind="ghost", width=90, height=22,
                                   font=T.font(12))
        self.log_toggle.pack(side="right")
        self.drive_lbl = W.label(sb, drive_free_space(self.get_active_folder()), 12, T.MUTED)
        self.drive_lbl.pack(side="right", padx=(0, 14))
        self.busy_bar = ctk.CTkProgressBar(sb, width=90, height=5, mode="indeterminate",
                                           progress_color=T.ACCENT, fg_color=T.SURFACE_ALT)

        self.log_drawer = ctk.CTkFrame(self.main, height=170, fg_color=T.SURFACE, corner_radius=0)
        self.log_drawer.pack_propagate(False)
        top = W.transparent(self.log_drawer)
        top.pack(fill="x", padx=20, pady=(8, 2))
        W.label(top, "Activity log", 12, T.TEXT, "semi").pack(side="left")
        W.button(top, "Clear", self.clear_logs, kind="ghost", width=56, height=24, font=T.font(12)).pack(side="right")
        W.button(top, "Copy", self.copy_logs, kind="ghost", width=56, height=24, font=T.font(12)).pack(side="right")
        self.log_box = W.textbox(self.log_drawer, font=T.mono(11))
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(2, 10))
        self.log_box.configure(state="disabled")

        self.workspace = W.transparent(self.main)
        self.workspace.pack(fill="both", expand=True, side="top")

    def _bind_shortcuts(self):
        for i, (key, *_rest) in enumerate(VIEWS, start=1):
            self.bind(f"<Control-Key-{i}>", lambda _e, k=key: self.show_view(k))
        self.bind("<Control-o>", lambda _e: self.browse_folder())
        self.bind("<Control-l>", lambda _e: self.toggle_log_drawer())
        self.bind("<Control-comma>", lambda _e: self.open_settings())
        self.bind("<F1>", lambda _e: self.open_help())

    # ------------------------------------------------------------------- views
    def register_view(self, view):
        self._instances.append(view)

    def unregister_view(self, view):
        if view in self._instances:
            self._instances.remove(view)

    def show_view(self, key):
        if key not in self.views:
            self.views[key] = VIEW_CLASSES[key](self.workspace, self)
        for k, view in self.views.items():
            if k == key:
                view.pack(fill="both", expand=True)
            else:
                view.pack_forget()
        for k, item in self.nav.items():
            item.set_active(k == key)
        self.current_key = key
        self.views[key].on_show()

    def detach_view(self, key):
        existing = self.detached.get(key)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return
        label = next(l for k, _c, l, _i in VIEWS if k == key)
        win = ctk.CTkToplevel(self, fg_color=T.BG)
        win.title(f"{label} - {APP_NAME}")
        win.geometry("1000x720")
        win.minsize(860, 600)
        win.after(250, lambda: self._safe_icon(win))
        self.detached[key] = win
        view = VIEW_CLASSES[key](win, self, detached=True)
        view.pack(fill="both", expand=True)
        view.on_show()
        self.log(f"Opened {label} in its own window.", "info")

    def _safe_icon(self, win):
        try:
            win.iconbitmap(self.icon_path)
        except Exception:
            pass

    # ------------------------------------------------------------ working folder
    def get_active_folder(self) -> str:
        return self.active_folder_var.get().strip().strip('"')

    def set_active_folder(self, folder: str):
        if not os.path.isdir(folder):
            return
        clean = os.path.abspath(folder)
        changed = clean.lower() != self.get_active_folder().lower()
        self.active_folder_var.set(clean)
        config.add_recent_folder(clean)
        self._refresh_recent_menu()
        self.refresh_drive_space()
        if changed:
            self.log(f"Working folder: {clean}", "info")
            for view in list(self._instances):
                view.on_folder_changed(clean)

    def _on_dir_typed(self):
        value = self.get_active_folder()
        if os.path.isdir(value):
            self.set_active_folder(value)
            self.focus_set()
        else:
            self.notify(f"Folder not found: {value}", "error")

    def browse_folder(self):
        initial = self.get_active_folder() if os.path.isdir(self.get_active_folder()) else startup_folder()
        chosen = filedialog.askdirectory(parent=self, initialdir=initial, title="Choose working folder")
        if chosen:
            self.set_active_folder(chosen)

    def _refresh_recent_menu(self):
        self._recents = config.get_recent_folders()
        labels = [self._short(f) for f in self._recents] or ["No recent folders"]
        self.recent_menu.configure(values=labels)
        self.recent_menu.set("Recent")

    @staticmethod
    def _short(path: str) -> str:
        return path if len(path) <= 44 else path[:16] + "..." + path[-25:]

    def _on_recent(self, label):
        self.recent_menu.set("Recent")
        for path in self._recents:
            if self._short(path) == label:
                return self.set_active_folder(path)

    def refresh_drive_space(self):
        self.drive_lbl.configure(text=drive_free_space(self.get_active_folder()))

    def open_current_in_explorer(self):
        path = self.get_active_folder()
        if os.path.isdir(path):
            os.startfile(path)
            self.log(f"Opened in Explorer: {path}", "info")
        else:
            self.notify("The working folder does not exist.", "error")

    def reveal(self, path):
        path = Path(path)
        try:
            if path.exists():
                subprocess.Popen(["explorer", f"/select,{path}"])
            else:
                os.startfile(str(path.parent))
        except OSError as exc:
            self.notify(f"Could not open Explorer: {exc}", "error")

    def open_current_in_terminal(self):
        path = self.get_active_folder()
        if not os.path.isdir(path):
            return self.notify("The working folder does not exist.", "error")
        try:
            if shutil.which("wt"):
                subprocess.Popen(["wt", "-d", path])
            else:
                subprocess.Popen(["powershell", "-NoExit"], cwd=path, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            self.log(f"Opened terminal in: {path}", "info")
        except OSError as exc:
            self.notify(f"Could not open terminal: {exc}", "error")

    # -------------------------------------------------------------- appearance
    def set_theme(self, mode: str):
        ctk.set_appearance_mode(mode)
        config.set("theme", mode)
        T.apply_ttk_style(self)

    def toggle_theme(self):
        self.set_theme("Light" if T.is_dark() else "Dark")

    def open_settings(self):
        SettingsDialog(self)

    def open_help(self):
        HelpDialog(self)

    # --------------------------------------------------------- feedback / status
    def log(self, message: str, level: str = "info"):
        now = datetime.now().strftime("%H:%M:%S")
        colors = {"info": T.SUCCESS, "success": T.SUCCESS, "warning": T.WARNING, "error": T.DANGER}
        marks = {"info": "INFO ", "success": "OK   ", "warning": "WARN ", "error": "ERROR"}
        self.status_dot.configure(text_color=colors.get(level, T.SUCCESS))
        self.status_lbl.configure(text=message if len(message) < 130 else message[:127] + "...")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{now}  {marks.get(level, 'INFO ')} {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def notify(self, message: str, kind: str = "success"):
        """Toast + log entry."""
        self.log(message, {"success": "success", "info": "info", "warning": "warning", "error": "error"}[kind])
        self.toasts.show(message, kind)

    def set_busy(self, busy: bool, text: str = ""):
        self._busy_count = max(0, self._busy_count + (1 if busy else -1))
        if self._busy_count:
            if text:
                self.status_lbl.configure(text=text)
            if not self.busy_bar.winfo_ismapped():
                self.busy_bar.pack(side="left", padx=(12, 0))
                self.busy_bar.start()
        else:
            self.busy_bar.stop()
            self.busy_bar.pack_forget()

    def toggle_log_drawer(self):
        if self.log_drawer.winfo_ismapped():
            self.log_drawer.pack_forget()
        else:
            self.log_drawer.pack(side="bottom", fill="x", before=self.workspace)
            # keep the drawer directly above the status bar
            self.log_drawer.lift()

    def clear_logs(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def copy_logs(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_box.get("1.0", "end-1c"))
        self.toasts.show("Log copied to clipboard.", "info")

    # ----------------------------------------------------------------------- exit
    def _on_close(self):
        try:
            config.data["window_geometry"] = self.geometry()
            config.data["last_folder"] = self.get_active_folder()
            config.data["last_view"] = self.current_key or "build"
            config.save()
        except Exception:
            pass
        self.destroy()
