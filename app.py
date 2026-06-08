import os
import sys
import random
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Slackers-Paradise"
APP_VERSION = "2.0.0"
APP_TAGLINE = ""

BG = "#0b1220"
SURFACE = "#111827"
SURFACE_2 = "#182235"
CARD = "#1e293b"
CARD_HOVER = "#24324a"
BORDER = "#334155"
FIELD = "#0f172a"
TEXT = "#f8fafc"
MUTED = "#a7b3c8"
BLUE = "#2563eb"
CYAN = "#0891b2"
GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"
PURPLE = "#7c3aed"
SLATE = "#475569"

INVALID_FOLDER_CHARS = set('<>:"/\\|?*')


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def startup_folder() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))


def shorten(path: str, limit: int = 64) -> str:
    if len(path) <= limit:
        return path
    keep_right = max(12, limit - 31)
    return path[:24] + "..." + path[-keep_right:]


def center_window(win: tk.Toplevel, parent: tk.Tk, width: int, height: int) -> None:
    parent.update_idletasks()
    x = parent.winfo_x() + max(0, (parent.winfo_width() - width) // 2)
    y = parent.winfo_y() + max(0, (parent.winfo_height() - height) // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


class ThreeDButton(tk.Canvas):
    def __init__(self, master, text, command=None, width=160, height=44,
                 color=BLUE, hover_color="#1d4ed8", text_color="white",
                 shadow="#020617", font=("Segoe UI", 10, "bold"), radius=14, **kwargs):
        super().__init__(master, width=width, height=height, bg=master.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.command = command
        self.button_text = text
        self.width = width
        self.height = height
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.shadow = shadow
        self.font = font
        self.radius = radius
        self._pressed = False
        self._draw(self.color, 0)
        self.bind("<Enter>", self._hover)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)

    def _round_rect(self, x1, y1, x2, y2, r, fill, outline=""):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, fill=fill, outline=outline)

    def _draw(self, fill, offset):
        self.delete("all")
        self._round_rect(5, 8 + (3 - offset), self.width - 3, self.height - 1, self.radius, self.shadow)
        self._round_rect(3, 3 + offset, self.width - 6, self.height - 9 + offset, self.radius, fill)
        self.create_line(18, 8 + offset, self.width - 25, 8 + offset, fill="#ffffff", width=1)
        self.create_text(self.width / 2 - 1, self.height / 2 - 4 + offset, text=self.button_text,
                         fill=self.text_color, font=self.font)

    def set_text(self, value):
        self.button_text = value
        self._draw(self.color, 0)

    def _hover(self, _event=None):
        if not self._pressed:
            self._draw(self.hover_color, 0)

    def _leave(self, _event=None):
        self._pressed = False
        self._draw(self.color, 0)

    def _press(self, _event=None):
        self._pressed = True
        self._draw(self.hover_color, 3)

    def _release(self, event=None):
        inside = event is not None and 0 <= event.x <= self.width and 0 <= event.y <= self.height
        self._pressed = False
        self._draw(self.hover_color if inside else self.color, 0)
        if inside and callable(self.command):
            self.command()


class FeatureWindow(tk.Toplevel):
    def __init__(self, app, title, subtitle, accent, size=(760, 520)):
        super().__init__(app)
        self.app = app
        self.accent = accent
        self.title(f"{title} - {APP_NAME}")
        self.configure(bg=BG)
        self.minsize(700, 520)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._set_icon()
        center_window(self, app, size[0], size[1])
        self._build_shell(title, subtitle)

    def _set_icon(self):
        icon_path = resource_path(os.path.join("assets", "app.ico"))
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_shell(self, title, subtitle):
        self.header = tk.Frame(self, bg=SURFACE)
        self.header.pack(fill="x")
        accent_bar = tk.Frame(self.header, bg=self.accent, width=7)
        accent_bar.pack(side="left", fill="y")
        header_content = tk.Frame(self.header, bg=SURFACE)
        header_content.pack(side="left", fill="x", expand=True, padx=22, pady=18)
        tk.Label(header_content, text=title, bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 21, "bold")).pack(anchor="w")
        tk.Label(header_content, text=subtitle, bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        self.body_holder = tk.Frame(self, bg=BG)
        self.body_holder.pack(fill="both", expand=True, padx=24, pady=18)

        self.body_canvas = tk.Canvas(self.body_holder, bg=BG, highlightthickness=0, bd=0)
        self.body_scrollbar = ttk.Scrollbar(self.body_holder, orient="vertical", command=self.body_canvas.yview)
        self.body_canvas.configure(yscrollcommand=self.body_scrollbar.set)

        self.body_scrollbar.pack(side="right", fill="y")
        self.body_canvas.pack(side="left", fill="both", expand=True)

        self.body = tk.Frame(self.body_canvas, bg=BG)
        self.body_window = self.body_canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._update_scroll_region)
        self.body_canvas.bind("<Configure>", self._fit_body_width)
        self.body_canvas.bind("<Enter>", self._bind_mousewheel)
        self.body_canvas.bind("<Leave>", self._unbind_mousewheel)


    def _update_scroll_region(self, _event=None):
        self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all"))

    def _fit_body_width(self, event):
        self.body_canvas.itemconfigure(self.body_window, width=event.width)

    def _bind_mousewheel(self, _event=None):
        self.body_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.body_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.body_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self.body_canvas.unbind_all("<MouseWheel>")
        self.body_canvas.unbind_all("<Button-4>")
        self.body_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            self.body_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.body_canvas.yview_scroll(3, "units")
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta:
                self.body_canvas.yview_scroll(delta * 3, "units")

    def close(self):
        self.app.forget_feature_window(self)
        self.destroy()

    def section(self, title=None):
        frame = tk.Frame(self.body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", pady=(0, 16))
        if title:
            tk.Label(frame, text=title, bg=CARD, fg=TEXT,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(14, 4))
        inner = tk.Frame(frame, bg=CARD)
        inner.pack(fill="x", padx=18, pady=(8 if title else 16, 16))
        return inner

    def field_row(self, parent, label, var, browse=None, button_text="Browse"):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=7)
        tk.Label(row, text=label, bg=CARD, fg=TEXT, width=18, anchor="w",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        entry = tk.Entry(row, textvariable=var, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                         relief="flat", bd=0)
        entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        if browse:
            ThreeDButton(row, button_text, browse, width=112, height=38,
                         color=SLATE, hover_color="#334155", radius=12).pack(side="right")
        return entry

    def info_text(self, parent, text, color=MUTED):
        tk.Label(parent, text=text, bg=CARD, fg=color, anchor="w", justify="left",
                 wraplength=650, font=("Segoe UI", 9)).pack(fill="x", pady=(2, 8))

    def action_row(self, parent):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        return row

    def add_action(self, parent, text, command, color, hover=None, width=160):
        ThreeDButton(parent, text, command, width=width, height=44, color=color,
                     hover_color=hover or color, radius=14).pack(side="left", padx=(0, 12), pady=(2, 0))

    def pick_folder(self, var, after=None):
        initial = var.get() if os.path.isdir(var.get()) else startup_folder()
        folder = filedialog.askdirectory(parent=self, initialdir=initial)
        if folder:
            var.set(folder)
            if after:
                after(folder)

    def pick_save_file(self, var):
        current = var.get().strip()
        initial_dir = os.path.dirname(current) if os.path.dirname(current) else startup_folder()
        initial_file = os.path.basename(current) or "List.txt"
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                                            initialdir=initial_dir, initialfile=initial_file)
        if path:
            var.set(path)


class BuildFolderWindow(FeatureWindow):
    def __init__(self, app):
        super().__init__(app, "Build-a-Folder", "Create one or many folders with clean validation.", BLUE, (780, 560))
        section = self.section("Folder setup")
        self.field_row(section, "Base folder", app.base_dir_var,
                       lambda: self.pick_folder(app.base_dir_var))
        tk.Label(section, text="Folder names", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 4))
        self.names_text = tk.Text(section, height=7, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                  relief="flat", bd=0, wrap="word")
        self.names_text.pack(fill="both", expand=False)
        self.info_text(section, "Tip: type one folder per line, or separate names with commas.")
        actions = self.action_row(section)
        self.add_action(actions, "Create folders", lambda: app.create_folders(app.base_dir_var.get(), self.names_text.get("1.0", "end"), self), BLUE, "#1d4ed8")
        self.add_action(actions, "Open base folder", lambda: app.open_folder(app.base_dir_var.get(), self), CYAN, "#0e7490")


class FolderFolioWindow(FeatureWindow):
    def __init__(self, app):
        super().__init__(app, "FolderFolio", "Export a clean List.txt from any folder.", GREEN, (780, 470))
        section = self.section("List export")
        self.field_row(section, "Source folder", app.folio_folder_var,
                       lambda: self.pick_folder(app.folio_folder_var, after=self.sync_output))
        self.field_row(section, "Output file", app.folio_output_var,
                       lambda: self.pick_save_file(app.folio_output_var), "Save as")
        self.info_text(section, "FolderFolio writes only the names of items inside the selected folder. It does not edit your files.")
        actions = self.action_row(section)
        self.add_action(actions, "Create List.txt", lambda: app.create_folder_list(app.folio_folder_var.get(), app.folio_output_var.get(), self), GREEN, "#15803d")
        self.add_action(actions, "Open source", lambda: app.open_folder(app.folio_folder_var.get(), self), CYAN, "#0e7490")

    def sync_output(self, folder):
        self.app.folio_output_var.set(os.path.join(folder, "List.txt"))


class RenameRouletteWindow(FeatureWindow):
    def __init__(self, app):
        super().__init__(app, "RenameRoulette", "Preview and rename files to random 4-digit names.", AMBER, (820, 620))
        section = self.section("Rename target")
        self.field_row(section, "Target folder", app.rename_folder_var,
                       lambda: self.pick_folder(app.rename_folder_var))
        self.info_text(section, "Safety note: this permanently changes file names. Preview first, then confirm before renaming.", "#fbbf24")
        actions = self.action_row(section)
        self.add_action(actions, "Preview names", self.preview_names, AMBER, "#b45309")
        self.add_action(actions, "Rename now", lambda: app.rename_files(app.rename_folder_var.get(), self), RED, "#b91c1c")

        preview_section = self.section("Preview")
        self.preview_box = tk.Text(preview_section, height=11, bg=FIELD, fg="#dbeafe",
                                   insertbackground=TEXT, relief="flat", bd=0, wrap="none")
        self.preview_box.pack(fill="both", expand=True)
        self.preview_box.insert("end", "Click Preview names to see a sample rename plan here.")
        self.preview_box.configure(state="disabled")

    def preview_names(self):
        text = self.app.preview_rename(self.app.rename_folder_var.get(), self, as_text=True)
        if text:
            self.preview_box.configure(state="normal")
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("end", text)
            self.preview_box.configure(state="disabled")


class ShortcutExecutorWindow(FeatureWindow):
    def __init__(self, app):
        super().__init__(app, "ShortcutExecutor", "Run Windows shortcut files from a selected folder.", PURPLE, (840, 660))
        selected = self.section("Custom shortcut folder")
        self.field_row(selected, "Shortcut folder", app.custom_shortcut_folder_var,
                       lambda: self.pick_folder(app.custom_shortcut_folder_var))
        self.info_text(selected, "Runs every .lnk file found directly inside the selected folder.")
        actions = self.action_row(selected)
        self.add_action(actions, "Run selected folder", lambda: app.run_shortcuts(app.custom_shortcut_folder_var.get(), self), PURPLE, "#6d28d9", 185)

        gaming = self.section("Gaming shortcut folder")
        self.field_row(gaming, "Gaming folder", app.shortcut_folder_var, None)
        self.info_text(gaming, "Default folder from the original BAT file: D:\\Gaming Shortcuts")
        actions2 = self.action_row(gaming)
        self.add_action(actions2, "Run D: shortcuts", lambda: app.run_shortcuts(app.shortcut_folder_var.get(), self), "#9333ea", "#7e22ce", 175)
        self.add_action(actions2, "Open folder", lambda: app.open_folder(app.shortcut_folder_var.get(), self), CYAN, "#0e7490")


class ToolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1060x700")
        self.minsize(920, 620)
        self.configure(bg=BG)
        self.option_add("*Font", ("Segoe UI", 10))
        self.feature_windows = {}

        self.base_dir_var = tk.StringVar(value=startup_folder())
        self.folio_folder_var = tk.StringVar(value=startup_folder())
        self.folio_output_var = tk.StringVar(value=os.path.join(startup_folder(), "List.txt"))
        self.rename_folder_var = tk.StringVar(value=startup_folder())
        self.shortcut_folder_var = tk.StringVar(value=r"D:\Gaming Shortcuts")
        self.custom_shortcut_folder_var = tk.StringVar(value=startup_folder())
        self.status_var = tk.StringVar(value="Ready")

        self._set_icon()
        self._configure_ttk()
        self._build_dashboard()
        self.log("Loaded all tools from the BAT package.")

    def _set_icon(self):
        icon_path = resource_path(os.path.join("assets", "app.ico"))
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _configure_ttk(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        try:
            style.configure("Vertical.TScrollbar", background=BORDER, troughcolor=BG, bordercolor=BG, arrowcolor=TEXT)
        except Exception:
            pass

    def _build_dashboard(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(22, 14))

        logo = tk.Frame(header, bg=BLUE, width=52, height=52)
        logo.pack(side="left", padx=(0, 14))
        logo.pack_propagate(False)
        tk.Label(logo, text="SP", bg=BLUE, fg="white", font=("Segoe UI", 13, "bold")).pack(expand=True)

        title_area = tk.Frame(header, bg=BG)
        title_area.pack(side="left", fill="x", expand=True)
        tk.Label(title_area, text=APP_NAME, bg=BG, fg=TEXT,
                 font=("Segoe UI", 25, "bold")).pack(anchor="w")

        badge = tk.Label(header, text=f"v{APP_VERSION}", bg="#0f766e", fg="white",
                         font=("Segoe UI", 10, "bold"), padx=13, pady=7)
        badge.pack(side="right")

        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True, padx=28, pady=(0, 18))

        left = tk.Frame(shell, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 18))
        right = tk.Frame(shell, bg=SURFACE, width=310, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(left, text="Tools", bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))
        grid = tk.Frame(left, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

        self._tool_tile(grid, 0, 0, "Build-a-Folder", "Create one or many folders with validation.",
                        "BF", BLUE, lambda: self.open_feature("build", BuildFolderWindow))
        self._tool_tile(grid, 0, 1, "FolderFolio", "Save a clean List.txt from any selected folder.",
                        "FF", GREEN, lambda: self.open_feature("folio", FolderFolioWindow))
        self._tool_tile(grid, 1, 0, "RenameRoulette", "Preview and randomize file names safely.",
                        "RR", AMBER, lambda: self.open_feature("rename", RenameRouletteWindow))
        self._tool_tile(grid, 1, 1, "ShortcutExecutor", "Run .lnk shortcuts from custom or gaming folders.",
                        "SE", PURPLE, lambda: self.open_feature("shortcuts", ShortcutExecutorWindow))

        self._right_panel(right)

        status = tk.Label(self, textvariable=self.status_var, bg=BG, fg=MUTED, anchor="w",
                          font=("Segoe UI", 9))
        status.pack(fill="x", padx=30, pady=(0, 8))

    def _tool_tile(self, parent, row, col, title, description, initials, color, command):
        outer = tk.Frame(parent, bg=BG)
        outer.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 9, 9 if col == 0 else 0), pady=(0 if row == 0 else 9, 9 if row == 0 else 0))
        card = tk.Frame(outer, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        card.bind("<Button-1>", lambda _e: command())

        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", padx=20, pady=(20, 10))
        icon = tk.Frame(top, bg=color, width=54, height=54)
        icon.pack(side="left", padx=(0, 14))
        icon.pack_propagate(False)
        tk.Label(icon, text=initials, bg=color, fg="white", font=("Segoe UI", 13, "bold")).pack(expand=True)
        title_box = tk.Frame(top, bg=CARD)
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(title_box, text=title, bg=CARD, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Separate window", bg=CARD, fg=color,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(3, 0))

        tk.Label(card, text=description, bg=CARD, fg=MUTED, justify="left",
                 wraplength=310, font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(4, 18))
        footer = tk.Frame(card, bg=CARD)
        footer.pack(fill="x", padx=20, pady=(0, 20), side="bottom")
        ThreeDButton(footer, "Open", command, width=120, height=40,
                     color=color, hover_color=color, radius=13).pack(side="left")

        # Keep every part of the card visually consistent. Earlier versions changed
        # only the parent frame on hover, which made child widgets look like mismatched
        # color strips. The card now uses a steady background and a clean hover border.
        def set_border(active):
            card.configure(highlightbackground=color if active else BORDER)

        def bind_clickable(widget):
            if not isinstance(widget, ThreeDButton):
                widget.bind("<Button-1>", lambda _e: command(), add="+")
                widget.bind("<Enter>", lambda _e: set_border(True), add="+")
                widget.bind("<Leave>", lambda _e: set_border(False), add="+")
            for child in widget.winfo_children():
                bind_clickable(child)

        bind_clickable(card)

    def _right_panel(self, parent):
        tk.Label(parent, text="Control Center", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(parent, text="Open one tool at a time or keep multiple tool windows available.",
                 bg=SURFACE, fg=MUTED, wraplength=260, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 14))

        info = tk.Frame(parent, bg=SURFACE_2, highlightbackground=BORDER, highlightthickness=1)
        info.pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(info, text="App folder", bg=SURFACE_2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(info, text=shorten(startup_folder(), 42), bg=SURFACE_2, fg=MUTED,
                 justify="left", wraplength=245, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))
        row = tk.Frame(info, bg=SURFACE_2)
        row.pack(fill="x", padx=12, pady=(0, 12))
        ThreeDButton(row, "Open folder", lambda: self.open_folder(startup_folder(), self), width=132, height=38,
                     color=CYAN, hover_color="#0e7490", radius=12).pack(side="left")

        tk.Label(parent, text="Activity", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(4, 6))
        self.log_box = tk.Text(parent, height=15, bg=FIELD, fg="#dbeafe", insertbackground=TEXT,
                               relief="flat", bd=0, wrap="word", font=("Segoe UI", 9))
        self.log_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log_box.configure(state="disabled")

    def open_feature(self, key, window_class):
        old = self.feature_windows.get(key)
        if old is not None and old.winfo_exists():
            old.lift()
            old.focus_force()
            return
        win = window_class(self)
        self.feature_windows[key] = win
        self.log(f"Opened {win.title().split(' - ')[0]}.")

    def forget_feature_window(self, window):
        for key, value in list(self.feature_windows.items()):
            if value is window:
                self.feature_windows.pop(key, None)
                break

    def log(self, message: str):
        self.status_var.set(message)
        if hasattr(self, "log_box"):
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"- {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

    def validate_folder(self, path: str, must_exist=True, parent=None):
        clean = path.strip().strip('"')
        if not clean:
            messagebox.showerror("Missing folder", "Please choose a folder first.", parent=parent)
            return None
        p = Path(clean)
        if must_exist and not p.exists():
            messagebox.showerror("Folder not found", f"This folder does not exist:\n\n{clean}", parent=parent)
            return None
        if must_exist and not p.is_dir():
            messagebox.showerror("Invalid folder", f"This is not a folder:\n\n{clean}", parent=parent)
            return None
        return p

    def create_folders(self, base_path: str, raw_names: str, parent=None):
        base = self.validate_folder(base_path, must_exist=True, parent=parent)
        if base is None:
            return
        names = [part.strip() for line in raw_names.strip().splitlines() for part in line.split(",") if part.strip()]
        if not names:
            messagebox.showerror("Missing folder names", "Type at least one folder name.", parent=parent)
            return

        created = []
        skipped = []
        invalid = []
        for name in names:
            if any(ch in INVALID_FOLDER_CHARS for ch in name) or name in {".", ".."}:
                invalid.append(name)
                continue
            target = base / name
            if target.exists():
                skipped.append(name)
                continue
            try:
                target.mkdir(parents=False, exist_ok=False)
                created.append(name)
            except Exception as exc:
                invalid.append(f"{name} ({exc})")

        msg = f"Created {len(created)} folder(s)."
        if skipped:
            msg += f" Skipped {len(skipped)} existing."
        if invalid:
            msg += f" Invalid or failed: {len(invalid)}."
        self.log(msg)
        messagebox.showinfo("Build-a-Folder", msg, parent=parent)

    def create_folder_list(self, folder_path: str, output_path: str, parent=None):
        folder = self.validate_folder(folder_path, must_exist=True, parent=parent)
        if folder is None:
            return
        output = Path(output_path.strip().strip('"') or str(folder / "List.txt"))
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            items = sorted([p.name for p in folder.iterdir()], key=str.lower)
            output.write_text("\n".join(items), encoding="utf-8")
        except PermissionError:
            messagebox.showerror("Permission denied", "Windows blocked writing the list file. Try a different output location.", parent=parent)
            return
        except Exception as exc:
            messagebox.showerror("Failed", f"Could not create list file:\n\n{exc}", parent=parent)
            return
        self.log(f"Saved {len(items)} item(s) to {shorten(str(output))}.")
        messagebox.showinfo("FolderFolio", f"Saved {len(items)} item(s) to:\n\n{output}", parent=parent)

    def _rename_plan(self, folder: Path):
        files = [p for p in folder.iterdir() if p.is_file()]
        if not files:
            return []
        if len(files) > 9000:
            raise RuntimeError("This tool uses 4-digit random names, so choose a folder with 9000 files or fewer.")
        used_names = {p.name.lower() for p in folder.iterdir()}
        plan = []
        for src in files:
            for _ in range(10000):
                new_name = f"{random.randint(1000, 9999)}{src.suffix}"
                if new_name.lower() not in used_names:
                    used_names.add(new_name.lower())
                    plan.append((src, folder / new_name))
                    break
            else:
                raise RuntimeError("Could not generate enough unique 4-digit names for this folder.")
        return plan

    def preview_rename(self, folder_path: str, parent=None, as_text=False):
        folder = self.validate_folder(folder_path, must_exist=True, parent=parent)
        if folder is None:
            return "" if as_text else None
        try:
            plan = self._rename_plan(folder)
        except Exception as exc:
            messagebox.showerror("Preview failed", str(exc), parent=parent)
            return "" if as_text else None
        if not plan:
            messagebox.showinfo("RenameRoulette", "No files found in this folder.", parent=parent)
            return "No files found in this folder." if as_text else None
        preview_lines = [f"{src.name}  ->  {dst.name}" for src, dst in plan[:30]]
        if len(plan) > 30:
            preview_lines.append(f"...and {len(plan) - 30} more")
        text = "\n".join(preview_lines)
        self.log(f"Previewed random names for {len(plan)} file(s).")
        if as_text:
            return text
        messagebox.showinfo("Rename preview", text, parent=parent)
        return None

    def rename_files(self, folder_path: str, parent=None):
        folder = self.validate_folder(folder_path, must_exist=True, parent=parent)
        if folder is None:
            return
        try:
            plan = self._rename_plan(folder)
        except Exception as exc:
            messagebox.showerror("Rename failed", str(exc), parent=parent)
            return
        if not plan:
            messagebox.showinfo("RenameRoulette", "No files found in this folder.", parent=parent)
            return
        answer = messagebox.askyesno(
            "Confirm rename",
            f"Rename {len(plan)} file(s) in:\n\n{folder}\n\nThis cannot be automatically undone. Continue?",
            parent=parent,
        )
        if not answer:
            self.log("Rename cancelled.")
            return
        renamed = 0
        failed = []
        for src, dst in plan:
            try:
                src.rename(dst)
                renamed += 1
            except Exception as exc:
                failed.append(f"{src.name}: {exc}")
        msg = f"Renamed {renamed} file(s)."
        if failed:
            msg += f" Failed: {len(failed)}."
        self.log(msg)
        if failed:
            messagebox.showwarning("RenameRoulette", msg + "\n\n" + "\n".join(failed[:5]), parent=parent)
        else:
            messagebox.showinfo("RenameRoulette", msg, parent=parent)

    def run_shortcuts(self, folder_path: str, parent=None):
        folder = self.validate_folder(folder_path, must_exist=True, parent=parent)
        if folder is None:
            return
        shortcuts = sorted(folder.glob("*.lnk"), key=lambda p: p.name.lower())
        if not shortcuts:
            messagebox.showinfo("ShortcutExecutor", f"No .lnk shortcut files found in:\n\n{folder}", parent=parent)
            self.log("No shortcuts found.")
            return
        if os.name != "nt":
            messagebox.showerror("Windows required", "Shortcut launching only works on Windows.", parent=parent)
            return
        answer = messagebox.askyesno("Run shortcuts", f"Run {len(shortcuts)} shortcut(s) from:\n\n{folder}?", parent=parent)
        if not answer:
            self.log("Shortcut launch cancelled.")
            return

        def task():
            launched = 0
            failed = []
            for shortcut in shortcuts:
                try:
                    os.startfile(str(shortcut))
                    launched += 1
                except Exception as exc:
                    failed.append(f"{shortcut.name}: {exc}")
            self.after(0, lambda: self._shortcut_done(launched, failed, parent))

        threading.Thread(target=task, daemon=True).start()

    def _shortcut_done(self, launched, failed, parent=None):
        msg = f"Launched {launched} shortcut(s)."
        if failed:
            msg += f" Failed: {len(failed)}."
        self.log(msg)
        if failed:
            messagebox.showwarning("ShortcutExecutor", msg + "\n\n" + "\n".join(failed[:5]), parent=parent)
        else:
            messagebox.showinfo("ShortcutExecutor", msg, parent=parent)

    def open_folder(self, folder_path: str, parent=None):
        folder = self.validate_folder(folder_path, must_exist=True, parent=parent)
        if folder is None:
            return
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
            self.log(f"Opened folder: {shorten(str(folder))}")
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc), parent=parent)


if __name__ == "__main__":
    app = ToolApp()
    app.mainloop()
