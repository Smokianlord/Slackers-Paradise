import os
import sys
import time
import shutil
import threading
import subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image

# Initialize Windows High-DPI Awareness before Tk / CTk init
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import customtkinter as ctk

from core.config import config, APP_NAME, APP_VERSION
from core.builder import execute_create_folders, preview_creation
from core.folio import scan_directory, export_scan_data, generate_ascii_tree, format_size
from core.renamer import renamer_engine
from core.shortcuts import scan_shortcuts, shortcut_runner
from core.cleaner import scan_user_temp, scan_empty_folders, scan_broken_shortcuts, execute_clean


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def startup_folder() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))


def get_drive_free_space(path_str: str) -> str:
    try:
        target = path_str if os.path.exists(path_str) else "."
        total, used, free = shutil.disk_usage(target)
        drive_letter = os.path.splitdrive(os.path.abspath(target))[0] or "Drive"
        return f"💽 {drive_letter} {free // (1024**3)} GB Free"
    except Exception:
        return "💽 Drive Ready"


def setup_treeview_style(is_dark=True):
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg = "#1e293b" if is_dark else "#f8fafc"
    fg = "#f8fafc" if is_dark else "#0f172a"
    field_bg = "#0f172a" if is_dark else "#ffffff"
    heading_bg = "#111827" if is_dark else "#e2e8f0"
    heading_fg = "#94a3b8" if is_dark else "#334155"
    select_bg = "#2563eb"
    select_fg = "#ffffff"

    style.configure(
        "Modern.Treeview",
        background=bg,
        foreground=fg,
        fieldbackground=field_bg,
        borderwidth=0,
        rowheight=26,
        font=("Segoe UI", 9)
    )
    style.configure(
        "Modern.Treeview.Heading",
        background=heading_bg,
        foreground=heading_fg,
        relief="flat",
        borderwidth=0,
        font=("Segoe UI", 9, "bold")
    )
    style.map(
        "Modern.Treeview",
        background=[("selected", select_bg)],
        foreground=[("selected", select_fg)]
    )
    style.map(
        "Modern.Treeview.Heading",
        background=[("active", "#1e293b" if is_dark else "#cbd5e1")]
    )


# -------------------------------------------------------------
# Views: BuildFolderView, FolderFolioView, RenameRouletteView, ShortcutExecutorView, SlackerCleanerView
# -------------------------------------------------------------

class BuildFolderView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        header.pack(fill="x", padx=16, pady=(12, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(title_box, text="📁 Build-a-Folder Pro", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Create nested directory trees, batch sequences, and project templates with instant validation.",
                     text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=12)).pack(anchor="w")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(btn_box, text="↗ Detach Window", width=120, height=32, fg_color="#334155", hover_color="#475569",
                      command=lambda: self.app.detach_view("build", BuildFolderView, "Build-a-Folder Pro")).pack(side="right")

        # Main content split
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Left pane: Inputs & Templates
        left = ctk.CTkFrame(content, fg_color=("gray90", "#1e293b"), corner_radius=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Templates strip
        tpl_frame = ctk.CTkFrame(left, fg_color="transparent")
        tpl_frame.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(tpl_frame, text="⚡ Quick Templates:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))

        templates = config.get("custom_templates", {})
        for tpl_name in list(templates.keys())[:4]:
            ctk.CTkButton(
                tpl_frame,
                text=tpl_name,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#0284c7",
                hover_color="#0369a1",
                command=lambda name=tpl_name: self._load_template(name)
            ).pack(side="left", padx=3)

        # Sequence generator helper
        seq_frame = ctk.CTkFrame(left, fg_color=("gray85", "#0f172a"), corner_radius=6)
        seq_frame.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(seq_frame, text="🔢 Sequence Pattern:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=10, pady=8)
        self.seq_entry = ctk.CTkEntry(seq_frame, placeholder_text="e.g. Episode_{01..12} or Chapter_{1..5}", height=28, width=240)
        self.seq_entry.pack(side="left", padx=6, pady=8)
        ctk.CTkButton(seq_frame, text="Insert Sequence", height=28, width=120, fg_color="#10b981", hover_color="#059669",
                      command=self._insert_sequence).pack(side="left", padx=6, pady=8)

        # Folder list text area
        ctk.CTkLabel(left, text="Folder paths to create (one per line, supports nested paths like 'src/components'):",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(8, 4))
        self.textbox = ctk.CTkTextbox(left, font=ctk.CTkFont(family="Consolas", size=12), corner_radius=6)
        self.textbox.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.textbox.insert("1.0", "src\nsrc/components\nsrc/assets/images\nsrc/utils\npublic\ntests\ndocs")

        # Bottom actions on left
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(4, 12))

        ctk.CTkButton(actions, text="✨ Create Folders Now", height=38, width=180, font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8", command=self.create_folders).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="👁 Preview", height=38, width=110, fg_color="#475569", hover_color="#334155",
                      command=self.preview).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="🧹 Clear", height=38, width=90, fg_color="#dc2626", hover_color="#b91c1c",
                      command=lambda: self.textbox.delete("1.0", "end")).pack(side="left")

        self.auto_open_var = ctk.BooleanVar(value=config.get("auto_open_after_create", False))
        ctk.CTkCheckBox(actions, text="Open folder when done", variable=self.auto_open_var).pack(side="right", padx=8)

        # Right pane: Live Treeview Preview & Stats
        right = ctk.CTkFrame(content, fg_color=("gray90", "#1e293b"), corner_radius=8, width=320)
        right.pack(side="right", fill="both", padx=(8, 0))
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="Validation & Status", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=14, pady=(12, 6))

        self.preview_tree = ttk.Treeview(right, columns=("Path", "Status"), show="headings", style="Modern.Treeview", selectmode="none")
        self.preview_tree.heading("Path", text="Folder Path")
        self.preview_tree.heading("Status", text="Status")
        self.preview_tree.column("Path", width=200, anchor="w")
        self.preview_tree.column("Status", width=90, anchor="center")

        tree_scroll = ctk.CTkScrollbar(right, orientation="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y", padx=(0, 8), pady=(0, 10))
        self.preview_tree.pack(fill="both", expand=True, padx=(10, 0), pady=(0, 10))

        self.stats_label = ctk.CTkLabel(right, text="Ready to validate.", text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=11))
        self.stats_label.pack(fill="x", padx=12, pady=(0, 12))

    def _load_template(self, tpl_name):
        tpls = config.get("custom_templates", {})
        if tpl_name in tpls:
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", "\n".join(tpls[tpl_name]))
            self.preview()

    def _insert_sequence(self):
        val = self.seq_entry.get().strip()
        if val:
            self.textbox.insert("end", f"\n{val}\n")
            self.seq_entry.delete(0, "end")
            self.preview()

    def preview(self):
        base = Path(self.app.get_active_folder())
        raw = self.textbox.get("1.0", "end")
        preview = preview_creation(base, raw)

        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        for it in preview["items"]:
            self.preview_tree.insert("", "end", values=(it["path"], it["status"].capitalize()))

        self.stats_label.configure(
            text=f"Total: {preview['total']} | New: {preview['new']} | Existing: {preview['existing']} | Invalid: {preview['invalid']}"
        )
        return preview

    def create_folders(self):
        base = Path(self.app.get_active_folder())
        if not base.exists():
            messagebox.showerror("Folder Error", f"Base directory does not exist:\n\n{base}")
            return

        raw = self.textbox.get("1.0", "end")
        res = execute_create_folders(base, raw)
        msg = f"Created {len(res['created'])} folder(s)."
        if res["skipped"]:
            msg += f" Skipped {len(res['skipped'])} existing."
        if res["failed"]:
            msg += f" Failed: {len(res['failed'])}."

        self.app.log(msg, "success" if res["created"] else "info")
        self.preview()
        messagebox.showinfo("Build-a-Folder Pro", msg)

        if self.auto_open_var.get() and res["created"]:
            self.app.open_current_in_explorer()


class FolderFolioView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.last_scan_result = None
        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        header.pack(fill="x", padx=16, pady=(12, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(title_box, text="📋 FolderFolio Pro", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Catalog and export directory trees with sizes, dates, and multi-format exports (TXT, ASCII Tree, CSV, Markdown, JSON).",
                     text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=12)).pack(anchor="w")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(btn_box, text="↗ Detach Window", width=120, height=32, fg_color="#334155", hover_color="#475569",
                      command=lambda: self.app.detach_view("folio", FolderFolioView, "FolderFolio Pro")).pack(side="right")

        # Controls bar
        ctrl_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        ctrl_frame.pack(fill="x", padx=16, pady=(0, 10))

        r1 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        r1.pack(fill="x", padx=14, pady=10)

        self.recursive_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r1, text="Recursive Scan", variable=self.recursive_var).pack(side="left", padx=(0, 14))

        self.inc_files_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r1, text="Include Files", variable=self.inc_files_var).pack(side="left", padx=(0, 14))

        self.inc_dirs_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r1, text="Include Folders", variable=self.inc_dirs_var).pack(side="left", padx=(0, 14))

        self.inc_hidden_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(r1, text="Hidden Files", variable=self.inc_hidden_var).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(r1, text="Pattern Filter:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(8, 4))
        self.pattern_entry = ctk.CTkEntry(r1, placeholder_text="e.g. *.png; *.jpg or *", width=160, height=28)
        self.pattern_entry.pack(side="left", padx=(0, 14))
        self.pattern_entry.insert(0, "*")

        ctk.CTkButton(r1, text="🔍 Scan Directory", height=32, width=140, font=ctk.CTkFont(weight="bold"),
                      fg_color="#10b981", hover_color="#059669", command=self.scan).pack(side="right")

        # Content Table & Output Previews
        table_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Treeview catalog
        cols = ("Name", "Type", "Size", "Modified", "Relative Path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Modern.Treeview")
        self.tree.heading("Name", text="Item Name")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Size", text="Size")
        self.tree.heading("Modified", text="Date Modified")
        self.tree.heading("Relative Path", text="Relative Path")

        self.tree.column("Name", width=220, anchor="w")
        self.tree.column("Type", width=70, anchor="center")
        self.tree.column("Size", width=90, anchor="e")
        self.tree.column("Modified", width=140, anchor="center")
        self.tree.column("Relative Path", width=300, anchor="w")

        scroll_y = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree.yview)
        scroll_x = ctk.CTkScrollbar(table_frame, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side="right", fill="y", padx=(0, 6), pady=6)
        scroll_x.pack(side="bottom", fill="x", padx=6, pady=(0, 6))
        self.tree.pack(fill="both", expand=True, padx=(6, 0), pady=(6, 0))

        # Bottom export footer
        footer = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        footer.pack(fill="x", padx=16, pady=(0, 12))

        f_inner = ctk.CTkFrame(footer, fg_color="transparent")
        f_inner.pack(fill="x", padx=14, pady=10)

        self.summary_label = ctk.CTkLabel(f_inner, text="Click 'Scan Directory' to catalog folder.", font=ctk.CTkFont(size=12, weight="bold"))
        self.summary_label.pack(side="left")

        ctk.CTkLabel(f_inner, text="Export Format:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(20, 6))
        self.fmt_menu = ctk.CTkOptionMenu(f_inner, values=["TXT List", "ASCII Tree", "CSV Table", "Markdown", "JSON"], width=130, height=32)
        self.fmt_menu.pack(side="left", padx=(0, 12))
        self.fmt_menu.set("TXT List")

        ctk.CTkButton(f_inner, text="📋 Copy to Clipboard", height=32, width=150, fg_color="#3b82f6", hover_color="#2563eb",
                      command=self.copy_to_clipboard).pack(side="right", padx=(8, 0))
        ctk.CTkButton(f_inner, text="💾 Export to File", height=32, width=140, fg_color="#10b981", hover_color="#059669",
                      command=self.export_file).pack(side="right")

    def scan(self):
        folder = Path(self.app.get_active_folder())
        if not folder.exists():
            messagebox.showerror("Folder Error", f"Directory does not exist:\n\n{folder}")
            return

        pats = [p.strip() for p in self.pattern_entry.get().split(";") if p.strip()] or ["*"]

        try:
            self.last_scan_result = scan_directory(
                folder,
                recursive=self.recursive_var.get(),
                include_files=self.inc_files_var.get(),
                include_dirs=self.inc_dirs_var.get(),
                include_hidden=self.inc_hidden_var.get(),
                patterns=pats
            )
        except Exception as exc:
            messagebox.showerror("Scan Error", str(exc))
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for it in self.last_scan_result["items"]:
            self.tree.insert("", "end", values=(it["name"], it["type"], it["size_formatted"], it["modified"], it["relative_path"]))

        summary = f"Files: {self.last_scan_result['total_files']} | Folders: {self.last_scan_result['total_dirs']} | Total Size: {self.last_scan_result['total_size_formatted']}"
        self.summary_label.configure(text=summary)
        self.app.log(f"Cataloged {folder.name}: {summary}", "success")

    def _get_export_extension(self):
        fmt = self.fmt_menu.get().split()[0].lower()
        if fmt == "ascii":
            return "tree", ".txt"
        elif fmt == "csv":
            return "csv", ".csv"
        elif fmt == "markdown":
            return "markdown", ".md"
        elif fmt == "json":
            return "json", ".json"
        return "txt", ".txt"

    def copy_to_clipboard(self):
        if not self.last_scan_result:
            self.scan()
        if not self.last_scan_result:
            return

        fmt, _ = self._get_export_extension()
        import tempfile
        tmp = Path(tempfile.gettempdir()) / f"folio_export_{int(time.time())}.txt"
        export_scan_data(self.last_scan_result, tmp, fmt)
        text = tmp.read_text(encoding="utf-8")
        try:
            tmp.unlink()
        except Exception:
            pass

        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.log("Catalog copied to clipboard!", "success")
        messagebox.showinfo("FolderFolio", "Catalog copied to clipboard!")

    def export_file(self):
        if not self.last_scan_result:
            self.scan()
        if not self.last_scan_result:
            return

        fmt, ext = self._get_export_extension()
        initial_file = f"Catalog_{Path(self.last_scan_result['root']).name}{ext}"
        target = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=ext,
            initialfile=initial_file,
            initialdir=self.last_scan_result["root"]
        )
        if target:
            export_scan_data(self.last_scan_result, Path(target), fmt)
            self.app.log(f"Saved catalog to {target}", "success")
            messagebox.showinfo("FolderFolio", f"Exported successfully to:\n\n{target}")


class RenameRouletteView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.current_plan = None
        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        header.pack(fill="x", padx=16, pady=(12, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(title_box, text="🎲 RenameRoulette Pro", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Safe multi-mode file renamer with two-phase atomic execution, conflict detection, and full 1-click Undo.",
                     text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=12)).pack(anchor="w")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(btn_box, text="↗ Detach Window", width=120, height=32, fg_color="#334155", hover_color="#475569",
                      command=lambda: self.app.detach_view("rename", RenameRouletteView, "RenameRoulette Pro")).pack(side="right")

        # Mode Selector Bar
        mode_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        mode_frame.pack(fill="x", padx=16, pady=(0, 10))

        r0 = ctk.CTkFrame(mode_frame, fg_color="transparent")
        r0.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(r0, text="Renaming Mode:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        self.mode_seg = ctk.CTkSegmentedButton(
            r0,
            values=["🎲 Roulette", "🔢 Sequential", "🔤 Replace/Add", "🕒 Date Stamp", "🔠 Case Transform"],
            command=self._on_mode_change
        )
        self.mode_seg.pack(side="left", fill="x", expand=True)
        self.mode_seg.set("🎲 Roulette")

        # Options Container
        self.opts_container = ctk.CTkFrame(mode_frame, fg_color=("gray85", "#0f172a"), corner_radius=6)
        self.opts_container.pack(fill="x", padx=14, pady=(0, 10))
        self._build_mode_options()

        # Comparison Preview Table
        table_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        cols = ("Original", "Arrow", "Proposed", "Status", "Note")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Modern.Treeview")
        self.tree.heading("Original", text="Original Name")
        self.tree.heading("Arrow", text="")
        self.tree.heading("Proposed", text="Proposed New Name")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Note", text="Validation Note")

        self.tree.column("Original", width=260, anchor="w")
        self.tree.column("Arrow", width=30, anchor="center")
        self.tree.column("Proposed", width=260, anchor="w")
        self.tree.column("Status", width=90, anchor="center")
        self.tree.column("Note", width=220, anchor="w")

        scroll_y = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.tree.pack(fill="both", expand=True, padx=(6, 0), pady=6)

        # Footer Action Bar
        footer = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        footer.pack(fill="x", padx=16, pady=(0, 12))

        f_inner = ctk.CTkFrame(footer, fg_color="transparent")
        f_inner.pack(fill="x", padx=14, pady=10)

        self.stats_lbl = ctk.CTkLabel(f_inner, text="Click 'Generate Preview' to test rename.", font=ctk.CTkFont(size=12, weight="bold"))
        self.stats_lbl.pack(side="left")

        ctk.CTkButton(f_inner, text="↺ Undo Last Rename", height=34, width=160, fg_color="#64748b", hover_color="#475569",
                      command=self.undo_rename).pack(side="right", padx=(8, 0))
        ctk.CTkButton(f_inner, text="⚡ Rename Files Now", height=34, width=170, font=ctk.CTkFont(weight="bold"),
                      fg_color="#dc2626", hover_color="#b91c1c", command=self.execute_rename).pack(side="right", padx=(8, 0))
        ctk.CTkButton(f_inner, text="👁 Generate Preview", height=34, width=150, fg_color="#f59e0b", hover_color="#d97706",
                      command=self.generate_preview).pack(side="right")

    def _build_mode_options(self):
        for child in self.opts_container.winfo_children():
            child.destroy()

        mode = self.mode_seg.get()

        if "Roulette" in mode:
            f = ctk.CTkFrame(self.opts_container, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(f, text="Random Type:").pack(side="left", padx=(0, 6))
            self.rand_type_menu = ctk.CTkOptionMenu(f, values=["4_digit (1000-9999)", "6_digit", "8_digit", "hex", "alphanumeric", "uuid"], width=180)
            self.rand_type_menu.pack(side="left", padx=(0, 14))

            ctk.CTkLabel(f, text="File Filter:").pack(side="left", padx=(0, 6))
            self.filter_entry = ctk.CTkEntry(f, placeholder_text="* or *.jpg; *.png", width=140)
            self.filter_entry.pack(side="left")
            self.filter_entry.insert(0, "*")

        elif "Sequential" in mode:
            f = ctk.CTkFrame(self.opts_container, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(f, text="Prefix:").pack(side="left", padx=(0, 4))
            self.seq_pfx = ctk.CTkEntry(f, width=110)
            self.seq_pfx.pack(side="left", padx=(0, 10))
            self.seq_pfx.insert(0, "Item_")

            ctk.CTkLabel(f, text="Start:").pack(side="left", padx=(0, 4))
            self.seq_start = ctk.CTkEntry(f, width=60)
            self.seq_start.pack(side="left", padx=(0, 10))
            self.seq_start.insert(0, "1")

            ctk.CTkLabel(f, text="Padding:").pack(side="left", padx=(0, 4))
            self.seq_pad = ctk.CTkOptionMenu(f, values=["1", "2", "3", "4", "5"], width=70)
            self.seq_pad.pack(side="left", padx=(0, 10))
            self.seq_pad.set("3")

            ctk.CTkLabel(f, text="Suffix:").pack(side="left", padx=(0, 4))
            self.seq_sfx = ctk.CTkEntry(f, width=90)
            self.seq_sfx.pack(side="left")

        elif "Replace" in mode:
            f = ctk.CTkFrame(self.opts_container, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(f, text="Find:").pack(side="left", padx=(0, 4))
            self.rep_find = ctk.CTkEntry(f, width=120)
            self.rep_find.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(f, text="Replace:").pack(side="left", padx=(0, 4))
            self.rep_replace = ctk.CTkEntry(f, width=120)
            self.rep_replace.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(f, text="Add Prefix:").pack(side="left", padx=(0, 4))
            self.rep_pfx = ctk.CTkEntry(f, width=90)
            self.rep_pfx.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(f, text="Add Suffix:").pack(side="left", padx=(0, 4))
            self.rep_sfx = ctk.CTkEntry(f, width=90)
            self.rep_sfx.pack(side="left")

        elif "Date" in mode:
            f = ctk.CTkFrame(self.opts_container, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(f, text="Adds 'YYYY-MM-DD_' date prefix using file modification date.").pack(side="left")

        elif "Case" in mode:
            f = ctk.CTkFrame(self.opts_container, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(f, text="Transform:").pack(side="left", padx=(0, 6))
            self.case_menu = ctk.CTkOptionMenu(f, values=["lower", "upper", "title", "snake", "kebab"], width=130)
            self.case_menu.pack(side="left")

    def _on_mode_change(self, _val):
        self._build_mode_options()
        self.generate_preview()

    def generate_preview(self):
        folder = Path(self.app.get_active_folder())
        if not folder.exists():
            messagebox.showerror("Folder Error", f"Target directory does not exist:\n\n{folder}")
            return

        mode_str = self.mode_seg.get()
        kwargs = {}

        if "Roulette" in mode_str:
            mode = "roulette"
            kwargs["random_type"] = self.rand_type_menu.get().split()[0]
            kwargs["extension_filter"] = self.filter_entry.get().strip() or "*"
        elif "Sequential" in mode_str:
            mode = "sequential"
            kwargs["seq_prefix"] = self.seq_pfx.get()
            try:
                kwargs["seq_start"] = int(self.seq_start.get())
            except Exception:
                kwargs["seq_start"] = 1
            kwargs["seq_padding"] = int(self.seq_pad.get())
            kwargs["seq_suffix"] = self.seq_sfx.get()
        elif "Replace" in mode_str:
            mode = "find_replace"
            kwargs["find_text"] = self.rep_find.get()
            kwargs["replace_text"] = self.rep_replace.get()
            kwargs["add_prefix"] = self.rep_pfx.get()
            kwargs["add_suffix"] = self.rep_sfx.get()
        elif "Date" in mode_str:
            mode = "date_stamp"
        elif "Case" in mode_str:
            mode = "case"
            kwargs["case_mode"] = self.case_menu.get()
        else:
            mode = "roulette"

        try:
            self.current_plan = renamer_engine.generate_plan(folder, mode=mode, **kwargs)
        except Exception as exc:
            messagebox.showerror("Preview Failed", str(exc))
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for it in self.current_plan["items"]:
            self.tree.insert("", "end", values=(it["old_name"], "➜", it["new_name"], it["status"].upper(), it["message"]))

        msg = f"Ready: {self.current_plan['ready']} | Unchanged: {self.current_plan['unchanged']} | Conflicts: {self.current_plan['conflicts']}"
        self.stats_lbl.configure(text=msg)
        self.app.log(f"Rename plan generated: {msg}", "info")

    def execute_rename(self):
        if not self.current_plan or not self.current_plan["items"]:
            self.generate_preview()
        if not self.current_plan:
            return

        if self.current_plan["conflicts"] > 0:
            if not messagebox.askyesno("Conflicts Detected", f"There are {self.current_plan['conflicts']} conflicting files which will be skipped.\n\nContinue with remaining {self.current_plan['ready']} files?"):
                return
        elif self.current_plan["ready"] == 0:
            messagebox.showinfo("RenameRoulette", "No files ready to be renamed.")
            return

        if config.get("confirm_destructive", True):
            if not messagebox.askyesno("Confirm Rename", f"Rename {self.current_plan['ready']} file(s) in:\n\n{self.current_plan['folder']}\n\n(You can undo this anytime using 'Undo Last Rename'). Proceed?"):
                return

        res = renamer_engine.execute_rename(self.current_plan)
        msg = f"Successfully renamed {res['renamed']} file(s)."
        if res["failed"]:
            msg += f" Failed: {len(res['failed'])}."

        self.app.log(msg, "success" if res["renamed"] else "warning")
        messagebox.showinfo("Rename Complete", msg)
        self.generate_preview()

    def undo_rename(self):
        res = renamer_engine.undo_last_rename()
        if res["restored"] > 0:
            msg = f"Successfully restored {res['restored']} file(s) back to original names!"
            self.app.log(msg, "success")
            messagebox.showinfo("Undo Complete", msg)
            self.generate_preview()
        else:
            msg = "Nothing to undo: " + ", ".join(str(f) for f in res["failed"])
            self.app.log(msg, "warning")
            messagebox.showwarning("Undo", msg)


class ShortcutExecutorView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.shortcuts = []
        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        header.pack(fill="x", padx=16, pady=(12, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(title_box, text="⚡ ShortcutExecutor Pro", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Inspect, filter, and launch shortcuts (.lnk, .url, .bat, .exe) with staggered timing and zero system freeze.",
                     text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=12)).pack(anchor="w")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(btn_box, text="↗ Detach Window", width=120, height=32, fg_color="#334155", hover_color="#475569",
                      command=lambda: self.app.detach_view("shortcuts", ShortcutExecutorView, "ShortcutExecutor Pro")).pack(side="right")

        # Preset Bar & Filters
        ctrl = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        ctrl.pack(fill="x", padx=16, pady=(0, 10))

        r0 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r0.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(r0, text="Quick Jumps:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        gaming_folder = config.get("default_gaming_folder")
        ctk.CTkButton(r0, text="🎮 Gaming Shortcuts", height=28, fg_color="#7c3aed", hover_color="#6d28d9",
                      command=lambda: self._set_folder(gaming_folder)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(r0, text="🖥 Desktop", height=28, fg_color="#0284c7", hover_color="#0369a1",
                      command=lambda: self._set_folder(str(Path.home() / "Desktop"))).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(r0, text="Search:").pack(side="left", padx=(8, 4))
        self.search_entry = ctk.CTkEntry(r0, placeholder_text="Filter shortcuts...", width=160, height=28)
        self.search_entry.pack(side="left", padx=(0, 12))
        self.search_entry.bind("<KeyRelease>", lambda _e: self._filter_shortcuts())

        ctk.CTkButton(r0, text="🔄 Rescan", height=28, width=80, fg_color="#475569", hover_color="#334155",
                      command=self.scan).pack(side="right")

        # Selection controls & Stagger delay
        r1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r1.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(r1, text="Select All", height=26, width=90, fg_color="#334155", command=self.select_all).pack(side="left", padx=(0, 6))
        ctk.CTkButton(r1, text="Deselect All", height=26, width=90, fg_color="#334155", command=self.deselect_all).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(r1, text="Stagger Delay:").pack(side="left", padx=(0, 4))
        self.delay_menu = ctk.CTkOptionMenu(r1, values=["0ms (Instant)", "250ms", "500ms (Recommended)", "1000ms", "2000ms"], width=170, height=26)
        self.delay_menu.pack(side="left")
        self.delay_menu.set("500ms (Recommended)")

        # Table of Shortcuts
        table_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        cols = ("Sel", "Name", "Type", "Status", "Target")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Modern.Treeview")
        self.tree.heading("Sel", text="[X]")
        self.tree.heading("Name", text="Shortcut Name")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Status", text="Target Status")
        self.tree.heading("Target", text="Target Path / Action")

        self.tree.column("Sel", width=40, anchor="center")
        self.tree.column("Name", width=220, anchor="w")
        self.tree.column("Type", width=70, anchor="center")
        self.tree.column("Status", width=90, anchor="center")
        self.tree.column("Target", width=450, anchor="w")

        self.tree.bind("<Button-1>", self._on_tree_click)

        scroll_y = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.tree.pack(fill="both", expand=True, padx=(6, 0), pady=6)

        # Footer Action Bar
        footer = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        footer.pack(fill="x", padx=16, pady=(0, 12))

        f_inner = ctk.CTkFrame(footer, fg_color="transparent")
        f_inner.pack(fill="x", padx=14, pady=10)

        self.status_lbl = ctk.CTkLabel(f_inner, text="Ready.", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_lbl.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(f_inner, width=180, height=12)
        self.progress_bar.pack(side="left", padx=14)
        self.progress_bar.set(0)

        self.abort_btn = ctk.CTkButton(f_inner, text="🛑 Abort", height=34, width=90, fg_color="#dc2626", hover_color="#b91c1c",
                                      state="disabled", command=self.abort_launch)
        self.abort_btn.pack(side="right", padx=(8, 0))

        self.launch_btn = ctk.CTkButton(f_inner, text="🚀 Launch Selected", height=34, width=170, font=ctk.CTkFont(weight="bold"),
                                       fg_color="#7c3aed", hover_color="#6d28d9", command=self.launch_selected)
        self.launch_btn.pack(side="right")

    def _set_folder(self, folder):
        if os.path.exists(folder):
            self.app.set_active_folder(folder)
            self.scan()
        else:
            messagebox.showinfo("Folder Info", f"Folder does not exist yet:\n\n{folder}\n\nYou can create or browse another folder.")

    def scan(self):
        folder = Path(self.app.get_active_folder())
        self.shortcuts = scan_shortcuts(folder)
        self._filter_shortcuts()

    def _filter_shortcuts(self):
        q = self.search_entry.get().strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        matched = 0
        for sc in self.shortcuts:
            if not q or q in sc["name"].lower() or q in sc["target"].lower():
                check = "✔" if sc["selected"] else " "
                valid_str = "Valid" if sc["is_valid"] else "Missing"
                self.tree.insert("", "end", values=(check, sc["name"], sc["type"], valid_str, sc["target"]), iid=sc["filename"])
                matched += 1

        selected_count = sum(1 for s in self.shortcuts if s["selected"])
        self.status_lbl.configure(text=f"Total: {len(self.shortcuts)} | Showing: {matched} | Selected: {selected_count}")

    def _on_tree_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            for sc in self.shortcuts:
                if sc["filename"] == row_id:
                    sc["selected"] = not sc["selected"]
                    break
            self._filter_shortcuts()

    def select_all(self):
        for sc in self.shortcuts:
            sc["selected"] = True
        self._filter_shortcuts()

    def deselect_all(self):
        for sc in self.shortcuts:
            sc["selected"] = False
        self._filter_shortcuts()

    def launch_selected(self):
        selected = [s for s in self.shortcuts if s["selected"]]
        if not selected:
            messagebox.showinfo("ShortcutExecutor", "No shortcuts selected to launch.")
            return

        delay_str = self.delay_menu.get().split("ms")[0]
        try:
            delay_ms = int(delay_str)
        except Exception:
            delay_ms = 500

        if config.get("confirm_destructive", True):
            if not messagebox.askyesno("Confirm Launch", f"Launch {len(selected)} shortcut(s) from:\n\n{self.app.get_active_folder()}?"):
                return

        self.launch_btn.configure(state="disabled")
        self.abort_btn.configure(state="normal")
        self.progress_bar.set(0)

        def on_prog(cur, total, name):
            self.after(0, lambda: self._update_progress(cur, total, name))

        def on_comp(launched, failed):
            self.after(0, lambda: self._finish_launch(launched, failed))

        shortcut_runner.launch_staggered(selected, delay_ms=delay_ms, on_progress=on_prog, on_complete=on_comp)

    def _update_progress(self, cur, total, name):
        self.progress_bar.set(cur / total)
        self.status_lbl.configure(text=f"Launching ({cur}/{total}): {name}")
        self.app.log(f"Launching shortcut: {name}", "info")

    def _finish_launch(self, launched, failed):
        self.launch_btn.configure(state="normal")
        self.abort_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        msg = f"Launched {launched} shortcut(s)."
        if failed:
            msg += f" Failed: {len(failed)}."
        self.status_lbl.configure(text=msg)
        self.app.log(msg, "success" if launched else "warning")
        messagebox.showinfo("Shortcut Launch Finished", msg)

    def abort_launch(self):
        shortcut_runner.abort()
        self.app.log("Shortcut launch aborted by user.", "warning")
        self.status_lbl.configure(text="Launch aborted.")


class SlackerCleanerView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.scanned_items = []
        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        header.pack(fill="x", padx=16, pady=(12, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(title_box, text="🧹 SlackerCleaner Pro", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Effortless cache and junk sweeper: safely clean Windows temp files, empty folders, and broken shortcuts in seconds.",
                     text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=12)).pack(anchor="w")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(btn_box, text="↗ Detach Window", width=120, height=32, fg_color="#334155", hover_color="#475569",
                      command=lambda: self.app.detach_view("cleaner", SlackerCleanerView, "SlackerCleaner Pro")).pack(side="right")

        # Scan category toggles
        ctrl = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        ctrl.pack(fill="x", padx=16, pady=(0, 10))

        r0 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r0.pack(fill="x", padx=14, pady=10)

        self.chk_temp = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r0, text="User Temp (%TEMP%)", variable=self.chk_temp).pack(side="left", padx=(0, 14))

        self.chk_empty = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r0, text="Empty Folders in Active Dir", variable=self.chk_empty).pack(side="left", padx=(0, 14))

        self.chk_broken = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r0, text="Broken Shortcuts in Active Dir", variable=self.chk_broken).pack(side="left", padx=(0, 14))

        ctk.CTkButton(r0, text="🔍 Scan for Junk", height=32, width=140, font=ctk.CTkFont(weight="bold"),
                      fg_color="#0284c7", hover_color="#0369a1", command=self.scan_junk).pack(side="right")

        # Table of Junk items
        table_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        cols = ("Sel", "Item", "Category", "Size", "Path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Modern.Treeview")
        self.tree.heading("Sel", text="[X]")
        self.tree.heading("Item", text="File / Folder")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Size", text="Size")
        self.tree.heading("Path", text="Location")

        self.tree.column("Sel", width=40, anchor="center")
        self.tree.column("Item", width=220, anchor="w")
        self.tree.column("Category", width=140, anchor="w")
        self.tree.column("Size", width=90, anchor="e")
        self.tree.column("Path", width=400, anchor="w")

        self.tree.bind("<Button-1>", self._on_tree_click)

        scroll_y = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.tree.pack(fill="both", expand=True, padx=(6, 0), pady=6)

        # Footer Action Bar
        footer = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=8)
        footer.pack(fill="x", padx=16, pady=(0, 12))

        f_inner = ctk.CTkFrame(footer, fg_color="transparent")
        f_inner.pack(fill="x", padx=14, pady=10)

        self.summary_lbl = ctk.CTkLabel(f_inner, text="Click 'Scan for Junk' to search for safe cleanable files.", font=ctk.CTkFont(size=12, weight="bold"))
        self.summary_lbl.pack(side="left")

        ctk.CTkButton(f_inner, text="Select All", height=28, width=80, fg_color="#334155", command=self.select_all).pack(side="left", padx=(14, 4))
        ctk.CTkButton(f_inner, text="Deselect All", height=28, width=90, fg_color="#334155", command=self.deselect_all).pack(side="left")

        ctk.CTkButton(f_inner, text="🧹 Clean Selected Items", height=34, width=180, font=ctk.CTkFont(weight="bold"),
                      fg_color="#dc2626", hover_color="#b91c1c", command=self.clean_selected).pack(side="right")

    def scan_junk(self):
        folder = Path(self.app.get_active_folder())
        items = []

        if self.chk_temp.get():
            items.extend(scan_user_temp())
        if self.chk_empty.get() and folder.exists():
            items.extend(scan_empty_folders(folder))
        if self.chk_broken.get() and folder.exists():
            items.extend(scan_broken_shortcuts(folder))

        self.scanned_items = items
        self._refresh_tree()

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_bytes = 0
        for idx, it in enumerate(self.scanned_items):
            check = "✔" if it["selected"] else " "
            self.tree.insert("", "end", iid=str(idx), values=(check, it["name"], it["category"], it["size_formatted"], str(it["path"])))
            if it["selected"]:
                total_bytes += it.get("size_bytes", 0)

        sel_count = sum(1 for it in self.scanned_items if it["selected"])
        self.summary_lbl.configure(text=f"Found: {len(self.scanned_items)} items | Selected: {sel_count} ({format_size(total_bytes)})")
        self.app.log(f"Junk scan found {len(self.scanned_items)} items ({format_size(total_bytes)}).", "info")

    def _on_tree_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id and row_id.isdigit():
            idx = int(row_id)
            if idx < len(self.scanned_items):
                self.scanned_items[idx]["selected"] = not self.scanned_items[idx]["selected"]
                self._refresh_tree()

    def select_all(self):
        for it in self.scanned_items:
            it["selected"] = True
        self._refresh_tree()

    def deselect_all(self):
        for it in self.scanned_items:
            it["selected"] = False
        self._refresh_tree()

    def clean_selected(self):
        to_clean = [it for it in self.scanned_items if it["selected"]]
        if not to_clean:
            messagebox.showinfo("SlackerCleaner", "No junk items selected.")
            return

        total_bytes = sum(it.get("size_bytes", 0) for it in to_clean)
        if not messagebox.askyesno("Confirm Clean", f"Permanently delete {len(to_clean)} selected items ({format_size(total_bytes)})?\n\n(Locked and in-use files will be safely skipped). Proceed?"):
            return

        res = execute_clean(to_clean)
        msg = f"Cleaned {res['cleaned']} item(s), freed {res['freed_formatted']}!"
        if res["skipped"] > 0:
            msg += f" ({res['skipped']} files currently in-use and skipped)."

        self.app.log(msg, "success")
        messagebox.showinfo("Clean Complete", msg)
        self.scan_junk()


# -------------------------------------------------------------
# Main Application Shell
# -------------------------------------------------------------

class SlackersParadiseApp(ctk.CTk):
    def __init__(self):
        # Configure CTk appearance
        theme = config.get("theme", "Dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme(config.get("color_theme", "blue"))

        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION} - Pro Launcher")
        self.geometry("1160x780")
        self.minsize(980, 680)

        # State
        self.active_folder_var = tk.StringVar(value=startup_folder())
        config.add_recent_folder(self.active_folder_var.get())
        self.status_text_var = tk.StringVar(value="Ready.")
        self.drive_space_var = tk.StringVar(value=get_drive_free_space(self.active_folder_var.get()))
        self.detached_windows = {}

        self._set_app_icon()
        setup_treeview_style(is_dark=(ctk.get_appearance_mode() == "Dark"))

        # Build UI layout
        self._build_top_toolbar()
        self._build_directory_bar()
        self._build_main_workspace()
        self._build_bottom_status_bar()

        # Keyboard shortcuts
        self._bind_shortcuts()

        # Initial view
        self.show_view("build")
        self.log(f"{APP_NAME} v{APP_VERSION} initialized successfully.", "success")

    def _set_app_icon(self):
        ico = resource_path(os.path.join("assets", "app.ico"))
        if os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

    def _build_top_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, height=54, fg_color=("gray85", "#111827"), corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        # Left brand icon & title
        left_box = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        left_box.pack(side="left", padx=(14, 10), pady=6)

        # Load PNG icon if possible
        png_path = resource_path(os.path.join("assets", "app.png"))
        if os.path.exists(png_path):
            try:
                pil_img = Image.open(png_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(30, 30))
                ctk.CTkLabel(left_box, image=ctk_img, text="").pack(side="left", padx=(0, 8))
            except Exception:
                pass

        ctk.CTkLabel(left_box, text=APP_NAME, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(left_box, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=10, weight="bold"),
                     fg_color="#0f766e", text_color="white", corner_radius=6, padx=6, pady=2).pack(side="left")

        # Center Navigation Buttons
        nav_box = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        nav_box.pack(side="left", padx=20, pady=6)

        self.nav_buttons = {}
        tabs = [
            ("build", "📁 Build-a-Folder", "#2563eb"),
            ("folio", "📋 FolderFolio", "#16a34a"),
            ("rename", "🎲 RenameRoulette", "#d97706"),
            ("shortcuts", "⚡ ShortcutExecutor", "#7c3aed"),
            ("cleaner", "🧹 SlackerCleaner", "#0284c7")
        ]

        for key, label, color in tabs:
            btn = ctk.CTkButton(
                nav_box,
                text=label,
                height=34,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="transparent",
                text_color=("gray10", "#f8fafc"),
                hover_color=("gray75", "#1e293b"),
                command=lambda k=key: self.show_view(k)
            )
            btn.pack(side="left", padx=3)
            self.nav_buttons[key] = (btn, color)

        # Right utility actions
        right_box = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        right_box.pack(side="right", padx=14, pady=6)

        ctk.CTkButton(right_box, text="📂 Explorer", width=85, height=32, fg_color="#334155", hover_color="#475569",
                      command=self.open_current_in_explorer).pack(side="left", padx=3)
        ctk.CTkButton(right_box, text="💻 Terminal", width=80, height=32, fg_color="#334155", hover_color="#475569",
                      command=self.open_current_in_terminal).pack(side="left", padx=3)
        ctk.CTkButton(right_box, text="🌓", width=36, height=32, fg_color="#334155", hover_color="#475569",
                      command=self.toggle_theme).pack(side="left", padx=3)
        ctk.CTkButton(right_box, text="⚙", width=36, height=32, fg_color="#334155", hover_color="#475569",
                      command=self.open_settings).pack(side="left", padx=3)
        ctk.CTkButton(right_box, text="❓", width=36, height=32, fg_color="#334155", hover_color="#475569",
                      command=self.open_help).pack(side="left", padx=3)

    def _build_directory_bar(self):
        dir_bar = ctk.CTkFrame(self, height=44, fg_color=("gray90", "#0f172a"), corner_radius=0)
        dir_bar.pack(fill="x", side="top")
        dir_bar.pack_propagate(False)

        inner = ctk.CTkFrame(dir_bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=6)

        ctk.CTkLabel(inner, text="Active Directory:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))

        self.dir_entry = ctk.CTkEntry(inner, textvariable=self.active_folder_var, height=30, font=ctk.CTkFont(family="Consolas", size=11))
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.dir_entry.bind("<Return>", lambda _e: self._on_dir_manual_change())

        ctk.CTkButton(inner, text="Browse...", width=80, height=30, fg_color="#2563eb", hover_color="#1d4ed8",
                      command=self.browse_folder).pack(side="left", padx=(0, 6))
        ctk.CTkButton(inner, text="📋 Copy", width=65, height=30, fg_color="#334155", hover_color="#475569",
                      command=self.copy_active_folder).pack(side="left", padx=(0, 6))

        # Recent folders dropdown
        recents = config.get_recent_folders()
        if recents:
            recent_names = [f"...{f[-25:]}" if len(f) > 28 else f for f in recents]
            self.recent_menu = ctk.CTkOptionMenu(
                inner,
                values=recent_names,
                width=110,
                height=30,
                command=lambda val: self._on_recent_selected(val, recents, recent_names)
            )
            self.recent_menu.set("Recent ▾")
            self.recent_menu.pack(side="left")

    def _on_recent_selected(self, val, recents, recent_names):
        try:
            idx = recent_names.index(val)
            self.set_active_folder(recents[idx])
        except Exception:
            pass

    def _on_dir_manual_change(self):
        val = self.active_folder_var.get().strip().strip('"')
        if os.path.isdir(val):
            self.set_active_folder(val)
        else:
            messagebox.showerror("Invalid Directory", f"Directory not found:\n\n{val}")

    def _build_main_workspace(self):
        self.workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace.pack(fill="both", expand=True, side="top")

        # Instantiate view frames
        self.views = {
            "build": BuildFolderView(self.workspace, self),
            "folio": FolderFolioView(self.workspace, self),
            "rename": RenameRouletteView(self.workspace, self),
            "shortcuts": ShortcutExecutorView(self.workspace, self),
            "cleaner": SlackerCleanerView(self.workspace, self)
        }

    def _build_bottom_status_bar(self):
        self.status_bar = ctk.CTkFrame(self, height=32, fg_color=("gray85", "#0b1220"), corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        inner = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=4)

        self.status_indicator = ctk.CTkLabel(inner, text="🟢", font=ctk.CTkFont(size=10))
        self.status_indicator.pack(side="left", padx=(0, 6))

        self.status_label = ctk.CTkLabel(inner, textvariable=self.status_text_var, font=ctk.CTkFont(size=11), text_color=("gray30", "#94a3b8"))
        self.status_label.pack(side="left")

        ctk.CTkButton(inner, text="Log Console ▾", height=22, width=95, font=ctk.CTkFont(size=10),
                      fg_color="transparent", text_color=("gray30", "#94a3b8"), hover_color=("gray75", "#1e293b"),
                      command=self.toggle_log_drawer).pack(side="right", padx=(8, 0))

        self.drive_label = ctk.CTkLabel(inner, textvariable=self.drive_space_var, font=ctk.CTkFont(size=11, weight="bold"),
                                        text_color=("gray30", "#60a5fa"))
        self.drive_label.pack(side="right")

        # Collapsible log drawer (placed above status bar)
        self.log_drawer = ctk.CTkFrame(self, height=130, fg_color=("gray90", "#111827"), corner_radius=0)
        self.log_drawer.pack_propagate(False)

        top_log = ctk.CTkFrame(self.log_drawer, fg_color="transparent")
        top_log.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(top_log, text="Live Activity Log", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        ctk.CTkButton(top_log, text="Clear", height=20, width=50, font=ctk.CTkFont(size=10), fg_color="#334155",
                      command=self.clear_logs).pack(side="right", padx=3)
        ctk.CTkButton(top_log, text="Copy", height=20, width=50, font=ctk.CTkFont(size=10), fg_color="#334155",
                      command=self.copy_logs).pack(side="right", padx=3)

        self.log_textbox = ctk.CTkTextbox(self.log_drawer, font=ctk.CTkFont(family="Consolas", size=10), corner_radius=4)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(2, 6))

    def _bind_shortcuts(self):
        self.bind("<Control-Key-1>", lambda _e: self.show_view("build"))
        self.bind("<Control-Key-2>", lambda _e: self.show_view("folio"))
        self.bind("<Control-Key-3>", lambda _e: self.show_view("rename"))
        self.bind("<Control-Key-4>", lambda _e: self.show_view("shortcuts"))
        self.bind("<Control-Key-5>", lambda _e: self.show_view("cleaner"))
        self.bind("<Control-o>", lambda _e: self.browse_folder())
        self.bind("<Control-O>", lambda _e: self.browse_folder())
        self.bind("<Control-l>", lambda _e: self.toggle_log_drawer())
        self.bind("<Control-L>", lambda _e: self.toggle_log_drawer())
        self.bind("<F1>", lambda _e: self.open_help())

    def show_view(self, key):
        for k, v in self.views.items():
            if k == key:
                v.pack(fill="both", expand=True)
            else:
                v.pack_forget()

        for k, (btn, color) in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=color, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "#f8fafc"))

    def get_active_folder(self) -> str:
        return self.active_folder_var.get()

    def set_active_folder(self, folder: str):
        if os.path.isdir(folder):
            clean = os.path.abspath(folder)
            self.active_folder_var.set(clean)
            config.add_recent_folder(clean)
            self.drive_space_var.set(get_drive_free_space(clean))
            self.log(f"Switched directory: {clean}", "info")

    def browse_folder(self):
        initial = self.get_active_folder() if os.path.isdir(self.get_active_folder()) else startup_folder()
        f = filedialog.askdirectory(parent=self, initialdir=initial)
        if f:
            self.set_active_folder(f)

    def copy_active_folder(self):
        self.clipboard_clear()
        self.clipboard_append(self.get_active_folder())
        self.log("Directory path copied to clipboard.", "info")

    def open_current_in_explorer(self):
        p = self.get_active_folder()
        if os.path.exists(p):
            try:
                if os.name == "nt":
                    os.startfile(p)
                else:
                    subprocess.Popen(["xdg-open", p])
                self.log(f"Opened Explorer: {p}", "info")
            except Exception as exc:
                messagebox.showerror("Error", str(exc))

    def open_current_in_terminal(self):
        p = self.get_active_folder()
        if os.path.exists(p):
            try:
                if os.name == "nt":
                    subprocess.Popen(["powershell", "-NoExit", "-Command", f"Set-Location '{p}'"])
                else:
                    subprocess.Popen(["x-terminal-emulator", f"--working-directory={p}"])
                self.log(f"Opened terminal in: {p}", "info")
            except Exception as exc:
                messagebox.showerror("Error", str(exc))

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        config.set("theme", new_mode)
        setup_treeview_style(is_dark=(new_mode == "Dark"))
        self.log(f"Theme switched to {new_mode}.", "info")

    def toggle_log_drawer(self):
        if self.log_drawer.winfo_ismapped():
            self.log_drawer.pack_forget()
        else:
            self.log_drawer.pack(fill="x", side="bottom", before=self.status_bar)

    def log(self, message: str, level: str = "info"):
        now = datetime.now().strftime("%H:%M:%S")
        symbols = {"info": "ℹ", "success": "✔", "warning": "⚠", "error": "✖"}
        indicators = {"info": "🟢", "success": "🟢", "warning": "🟡", "error": "🔴"}

        sym = symbols.get(level, "•")
        self.status_indicator.configure(text=indicators.get(level, "🟢"))
        self.status_text_var.set(f"[{now}] {message}")

        if hasattr(self, "log_textbox"):
            self.log_textbox.insert("end", f"[{now}] {sym} {message}\n")
            self.log_textbox.see("end")

    def clear_logs(self):
        if hasattr(self, "log_textbox"):
            self.log_textbox.delete("1.0", "end")

    def copy_logs(self):
        if hasattr(self, "log_textbox"):
            text = self.log_textbox.get("1.0", "end")
            self.clipboard_clear()
            self.clipboard_append(text)
            self.log("Logs copied to clipboard.", "info")

    def detach_view(self, key, view_class, title):
        old_win = self.detached_windows.get(key)
        if old_win is not None and old_win.winfo_exists():
            old_win.lift()
            old_win.focus_force()
            return

        win = ctk.CTkToplevel(self)
        win.title(f"{title} - {APP_NAME}")
        win.geometry("880x600")
        win.minsize(700, 500)
        self.detached_windows[key] = win

        # Add view inside top level
        view_instance = view_class(win, self)
        view_instance.pack(fill="both", expand=True)

        self.log(f"Detached {title} into separate window.", "info")

    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings - Slackers-Paradise")
        win.geometry("540x420")
        win.resizable(False, False)

        ctk.CTkLabel(win, text="⚙ Preferences & Settings", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(18, 12))

        # Gaming shortcuts folder setting
        f1 = ctk.CTkFrame(win, fg_color=("gray90", "#1e293b"), corner_radius=8)
        f1.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(f1, text="Default Gaming Folder:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        gaming_var = tk.StringVar(value=config.get("default_gaming_folder"))
        r = ctk.CTkFrame(f1, fg_color="transparent")
        r.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkEntry(r, textvariable=gaming_var, height=30).pack(side="left", fill="x", expand=True, padx=(0, 8))
        def pick_gaming():
            f = filedialog.askdirectory(parent=win, initialdir=gaming_var.get())
            if f:
                gaming_var.set(f)
                config.set("default_gaming_folder", f)
        ctk.CTkButton(r, text="Browse", width=70, height=30, command=pick_gaming).pack(side="right")

        # Confirm destructive actions toggle
        f2 = ctk.CTkFrame(win, fg_color=("gray90", "#1e293b"), corner_radius=8)
        f2.pack(fill="x", padx=20, pady=6)
        confirm_var = ctk.BooleanVar(value=config.get("confirm_destructive", True))
        def toggle_confirm():
            config.set("confirm_destructive", confirm_var.get())
        ctk.CTkCheckBox(f2, text="Ask confirmation before bulk rename / shortcut launch / clean", variable=confirm_var,
                        command=toggle_confirm).pack(anchor="w", padx=12, pady=12)

        # Reset button
        btn_box = ctk.CTkFrame(win, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(16, 12))
        ctk.CTkButton(btn_box, text="Close", width=100, height=32, command=win.destroy).pack(side="right")

    def open_help(self):
        win = ctk.CTkToplevel(self)
        win.title("Help & Shortcuts - Slackers-Paradise")
        win.geometry("620x520")

        ctk.CTkLabel(win, text="Slackers-Paradise Pro v3.0 Help", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=22, pady=(18, 6))
        ctk.CTkLabel(win, text="Productivity launcher for Windows developers, gamers, and slackers.",
                     text_color=("gray40", "#94a3b8"), font=ctk.CTkFont(size=12)).pack(anchor="w", padx=22, pady=(0, 12))

        box = ctk.CTkTextbox(win, font=ctk.CTkFont(size=12), corner_radius=8)
        box.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        help_text = """KEYBOARD SHORTCUTS:
  Ctrl+1         Switch to Build-a-Folder Pro
  Ctrl+2         Switch to FolderFolio Pro
  Ctrl+3         Switch to RenameRoulette Pro
  Ctrl+4         Switch to ShortcutExecutor Pro
  Ctrl+5         Switch to SlackerCleaner Pro
  Ctrl+O         Browse Working Directory
  Ctrl+L         Toggle Live Activity Log Drawer
  F1             Open this Help Guide

FEATURE HIGHLIGHTS:
  📁 Build-a-Folder Pro:
     - Supports nested subfolder paths (e.g. 'src/components/ui')
     - Sequence Generator: Episode_{01..12} expands automatically
     - 1-click Project Templates (Web, Python, Media, School)
     - Reserved Windows names validation (CON, PRN, AUX, etc.)

  📋 FolderFolio Pro:
     - Multi-format catalog exports: TXT, ASCII Tree, CSV, Markdown, JSON
     - Recursive or shallow folder scans with file size & date metadata
     - 1-click 'Copy to Clipboard' for sharing on Discord/GitHub/Notion

  🎲 RenameRoulette Pro:
     - Multiple Renaming Modes: Random roulette, Sequential, Replace, Date, Case
     - Two-phase safe atomic renaming with zero name collisions
     - 1-click 'Undo Last Rename' restores all files instantly

  ⚡ ShortcutExecutor Pro:
     - Scans .lnk, .url, .bat, .cmd, .exe
     - Staggered execution delay prevents computer freeze when launching multiple games
     - Real-time search filter and selection checkboxes

  🧹 SlackerCleaner Pro:
     - Safely scan and sweep Windows %TEMP%, empty folders, and broken shortcuts
     - Safe deletion skips locked/in-use files gracefully
"""
        box.insert("1.0", help_text)
        box.configure(state="disabled")


if __name__ == "__main__":
    app = SlackersParadiseApp()
    app.mainloop()
