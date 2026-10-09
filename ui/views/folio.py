from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from core.folio import export_scan_data, format_size, render_scan_data, scan_directory
from ui import theme as T
from ui import widgets as W
from ui.base import BaseView

FORMATS = {
    # label: (format key, extension)
    "Plain list (.txt)": ("txt", ".txt"),
    "Folder tree (.txt)": ("tree", ".txt"),
    "Spreadsheet (.csv)": ("csv", ".csv"),
    "Markdown table (.md)": ("markdown", ".md"),
    "JSON (.json)": ("json", ".json"),
}
MAX_ROWS = 5000


class FolderFolioView(BaseView):
    key = "folio"
    title = "FolderFolio"
    subtitle = "Catalog any folder and export it as a list, tree, spreadsheet, Markdown or JSON."

    def build(self, body):
        self.scan = None
        self._scanning = False

        # --- scan options ---------------------------------------------------
        opts = W.Card(body)
        opts.pack(fill="x", pady=(0, 12))
        row = W.transparent(opts)
        row.pack(fill="x", padx=18, pady=14)

        self.recursive_var = ctk.BooleanVar(value=True)
        self.files_var = ctk.BooleanVar(value=True)
        self.dirs_var = ctk.BooleanVar(value=True)
        self.hidden_var = ctk.BooleanVar(value=False)
        for text, var in (("Include sub-folders", self.recursive_var), ("Files", self.files_var),
                          ("Folders", self.dirs_var), ("Hidden", self.hidden_var)):
            W.switch(row, text, var).pack(side="left", padx=(0, 18))

        self.scan_btn = W.button(row, "Scan folder", self.start_scan, kind="primary", width=130)
        self.scan_btn.pack(side="right")
        self.pattern = W.entry(row, "*.png; *.jpg", width=170)
        self.pattern.pack(side="right", padx=(0, 12))
        self.pattern.insert(0, "*")
        self.pattern.bind("<Return>", lambda _e: self.start_scan())
        W.label(row, "Match", 12, T.MUTED).pack(side="right", padx=(0, 8))

        # --- stats ------------------------------------------------------------
        tiles = W.transparent(body)
        tiles.pack(fill="x", pady=(0, 12))
        for i in range(4):
            tiles.grid_columnconfigure(i, weight=1, uniform="t")
        self.t_files = W.StatTile(tiles, "Files", "-")
        self.t_dirs = W.StatTile(tiles, "Folders", "-")
        self.t_size = W.StatTile(tiles, "Total size", "-")
        self.t_type = W.StatTile(tiles, "Most common type", "-")
        for i, tile in enumerate((self.t_files, self.t_dirs, self.t_size, self.t_type)):
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))

        # --- results -------------------------------------------------------------
        results = W.Card(body)
        results.pack(fill="both", expand=True)
        bar = W.transparent(results)
        bar.pack(fill="x", padx=18, pady=(14, 8))
        self.search = W.entry(bar, "Filter results...", width=280, height=34)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda _e: self._render_rows())
        self.count_lbl = W.label(bar, "", 12, T.MUTED)
        self.count_lbl.pack(side="right")

        foot = W.transparent(results)
        foot.pack(side="bottom", fill="x", padx=18, pady=(0, 14))
        holder = W.transparent(results)
        holder.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.table = W.DataTable(holder, [
            {"id": "name", "title": "Name", "width": 240, "stretch": True},
            {"id": "type", "title": "Type", "width": 80, "anchor": "center"},
            {"id": "size", "title": "Size", "width": 90, "anchor": "e"},
            {"id": "modified", "title": "Modified", "width": 150, "anchor": "center"},
            {"id": "path", "title": "Path", "width": 300, "stretch": True},
        ], on_double_click=self._open_selected)
        self.table.pack(fill="both", expand=True)
        self.empty = W.EmptyState(holder, "folio", "No catalog yet",
                                  "Choose a working folder, then press Scan folder.\nDouble-click any row to reveal it in Explorer.")
        self.empty.place(relx=0.5, rely=0.5, anchor="center")

        W.label(foot, "Export as", 12, T.MUTED).pack(side="left", padx=(0, 8))
        self.fmt_menu = W.option_menu(foot, list(FORMATS), width=190)
        self.fmt_menu.pack(side="left")
        W.button(foot, "Save to file...", self.export_file, kind="primary", width=140).pack(side="right")
        W.button(foot, "Copy to clipboard", self.copy_to_clipboard, kind="secondary", width=160).pack(side="right", padx=(0, 8))

    # ----------------------------------------------------------------- scan
    def refresh(self):
        # Results belong to the previous folder; clear them rather than showing stale data.
        self.scan = None
        self.table.clear()
        self.empty.place(relx=0.5, rely=0.5, anchor="center")
        for tile in (self.t_files, self.t_dirs, self.t_size, self.t_type):
            tile.set("-")
        self.count_lbl.configure(text="")

    def start_scan(self):
        if self._scanning:
            return
        folder = Path(self.app.get_active_folder())
        if not folder.is_dir():
            return self.app.notify(f"Folder not found: {folder}", "error")
        patterns = [p.strip() for p in self.pattern.get().split(";") if p.strip()] or ["*"]
        options = dict(recursive=self.recursive_var.get(), include_files=self.files_var.get(),
                       include_dirs=self.dirs_var.get(), include_hidden=self.hidden_var.get(), patterns=patterns)

        self._scanning = True
        self.scan_btn.configure(text="Scanning...", state="disabled")
        self.app.set_busy(True, "Scanning folder...")
        self.run_async(lambda: scan_directory(folder, **options), self._scan_done)

    def _scan_done(self, result, error):
        self._scanning = False
        self.scan_btn.configure(text="Scan folder", state="normal")
        self.app.set_busy(False)
        if error:
            return self.app.notify(f"Scan failed: {error}", "error")
        self.scan = result
        self._dirty = False
        self.t_files.set(f"{result['total_files']:,}")
        self.t_dirs.set(f"{result['total_dirs']:,}")
        self.t_size.set(result["total_size_formatted"])
        exts = result["extensions"]
        top = max(exts, key=exts.get) if exts else ""
        self.t_type.set((top.upper().lstrip(".") or "No extension") if exts else "-")
        self._render_rows()
        self.app.log(f"Cataloged {Path(result['root']).name}: {result['total_files']} files, "
                     f"{result['total_dirs']} folders, {result['total_size_formatted']}.", "success")

    # ---------------------------------------------------------------- table
    def _visible_items(self):
        if not self.scan:
            return []
        q = self.search.get().strip().lower()
        items = self.scan["items"]
        if not q:
            return items
        return [it for it in items if q in it["name"].lower() or q in it["relative_path"].lower() or q in it["type"].lower()]

    def _render_rows(self):
        self.table.clear()
        if not self.scan:
            return
        items = self._visible_items()
        for it in items[:MAX_ROWS]:
            self.table.insert((it["name"], it["type"], it["size_formatted"], it["modified"], it["relative_path"]))
        if self.scan["items"]:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        shown = min(len(items), MAX_ROWS)
        text = f"{len(items):,} item{'s' if len(items) != 1 else ''}"
        if len(items) > MAX_ROWS:
            text = f"Showing first {shown:,} of {len(items):,} (exports include everything)"
        self.count_lbl.configure(text=text)

    def _open_selected(self, _event=None):
        sel = self.table.selection()
        if sel and self.scan:
            rel = self.table.row_values(sel[0])[4]
            self.app.reveal(Path(self.scan["root"]) / rel)

    # --------------------------------------------------------------- export
    def _export_scan(self):
        """The scan, narrowed to whatever the filter box currently shows."""
        items = self._visible_items()
        files = [i for i in items if not i["is_dir"]]
        total = sum(i["size_bytes"] for i in files)
        return {**self.scan, "items": items, "total_files": len(files),
                "total_dirs": len(items) - len(files), "total_size_bytes": total,
                "total_size_formatted": format_size(total)}

    def _ensure_scan(self):
        if self.scan is None:
            self.app.notify("Scan a folder first.", "info")
            return False
        return True

    def copy_to_clipboard(self):
        if not self._ensure_scan():
            return
        fmt, _ = FORMATS[self.fmt_menu.get()]
        text = render_scan_data(self._export_scan(), fmt)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.notify(f"Copied {len(text.splitlines()):,} lines to the clipboard.", "success")

    def export_file(self):
        if not self._ensure_scan():
            return
        fmt, ext = FORMATS[self.fmt_menu.get()]
        root = self.scan["root"]
        target = filedialog.asksaveasfilename(
            parent=self.toplevel, defaultextension=ext, initialdir=root,
            initialfile=f"Catalog_{Path(root).name or 'drive'}{ext}",
            filetypes=[(self.fmt_menu.get(), f"*{ext}"), ("All files", "*.*")])
        if not target:
            return
        try:
            export_scan_data(self._export_scan(), Path(target), fmt)
        except OSError as exc:
            return self.app.notify(f"Could not save file: {exc}", "error")
        self.app.notify(f"Saved {Path(target).name}", "success")
        self.app.log(f"Saved catalog to {target}", "success")
