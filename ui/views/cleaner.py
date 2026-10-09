from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from core.cleaner import (
    RECYCLABLE, execute_clean, is_protected_root, scan_broken_shortcuts, scan_empty_folders, scan_user_temp,
)
from core.config import config
from core.folio import format_size
from ui import theme as T
from ui import widgets as W
from ui.base import BaseView

AGES = {"1 hour": 1, "24 hours": 24, "3 days": 72, "7 days": 168, "Any age": 0}
CHECKED, UNCHECKED = "●", "○"


class SlackerCleanerView(BaseView):
    key = "cleaner"
    title = "SlackerCleaner"
    subtitle = "Find and remove junk safely. Nothing is deleted until you review and confirm."

    def build(self, body):
        self.items = []
        self._scanning = False

        # --- what to scan ---------------------------------------------------------
        opts = W.Card(body)
        opts.pack(fill="x", pady=(0, 12))
        inner = W.transparent(opts)
        inner.pack(fill="x", padx=18, pady=14)
        self.scan_btn = W.button(inner, "Scan for junk", self.start_scan, kind="primary", width=140, height=40)
        self.scan_btn.pack(side="right", anchor="n")

        rows = W.transparent(inner)
        rows.pack(side="left", fill="x", expand=True)
        self.temp_var = ctk.BooleanVar(value=True)
        self.empty_var = ctk.BooleanVar(value=True)
        self.broken_var = ctk.BooleanVar(value=True)

        r1 = W.transparent(rows)
        r1.pack(fill="x", pady=(0, 8))
        W.switch(r1, "Temporary files", self.temp_var).pack(side="left")
        W.label(r1, "in %TEMP% not modified for", 12, T.MUTED).pack(side="left", padx=(10, 6))
        self.age_menu = W.option_menu(r1, list(AGES), width=110, height=28)
        self.age_menu.set("24 hours")
        self.age_menu.pack(side="left")

        r2 = W.transparent(rows)
        r2.pack(fill="x", pady=(0, 8))
        W.switch(r2, "Empty folders", self.empty_var).pack(side="left")
        W.label(r2, "inside the working folder (nested empties included)", 12, T.MUTED).pack(side="left", padx=10)

        r3 = W.transparent(rows)
        r3.pack(fill="x")
        W.switch(r3, "Broken shortcuts", self.broken_var).pack(side="left")
        W.label(r3, "in the working folder whose target no longer exists", 12, T.MUTED).pack(side="left", padx=10)

        # --- stats --------------------------------------------------------------------
        tiles = W.transparent(body)
        tiles.pack(fill="x", pady=(0, 12))
        for i in range(3):
            tiles.grid_columnconfigure(i, weight=1, uniform="t")
        self.t_found = W.StatTile(tiles, "Items found", "-")
        self.t_sel = W.StatTile(tiles, "Selected", "-")
        self.t_size = W.StatTile(tiles, "Space to free", "-")
        for i, tile in enumerate((self.t_found, self.t_sel, self.t_size)):
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        # --- results ---------------------------------------------------------------------
        card = W.Card(body)
        card.pack(fill="both", expand=True)
        foot = W.transparent(card)
        foot.pack(side="bottom", fill="x", padx=18, pady=(0, 16))
        holder = W.transparent(card)
        holder.pack(fill="both", expand=True, padx=18, pady=(16, 8))
        self.table = W.DataTable(holder, [
            {"id": "sel", "title": "", "width": 44, "anchor": "center", "sort": False},
            {"id": "name", "title": "Item", "width": 230, "stretch": True},
            {"id": "cat", "title": "Type", "width": 120},
            {"id": "size", "title": "Size", "width": 90, "anchor": "e"},
            {"id": "where", "title": "Location", "width": 360, "stretch": True},
        ], on_click=self._on_click)
        self.table.pack(fill="both", expand=True)
        self.empty = W.EmptyState(holder, "cleaner", "Nothing scanned yet",
                                  "Choose what to look for and press Scan for junk.\nYou will see every item before anything is removed.")
        self.empty.place(relx=0.5, rely=0.5, anchor="center")

        W.button(foot, "Select all", lambda: self._select(True), kind="secondary", width=90, height=34).pack(side="left", padx=(0, 6))
        W.button(foot, "None", lambda: self._select(False), kind="secondary", width=64, height=34).pack(side="left", padx=(0, 14))
        self.note_lbl = W.label(foot, "", 12, T.MUTED)
        self.note_lbl.pack(side="left")
        self.clean_btn = W.button(foot, "Clean selected", self.clean_selected, kind="danger", width=170, height=40, state="disabled")
        self.clean_btn.pack(side="right")

    # ------------------------------------------------------------------ scan
    def refresh(self):
        # Results from another folder are no longer meaningful.
        self.items = []
        self._render()

    def start_scan(self):
        if self._scanning:
            return
        folder = Path(self.app.get_active_folder())
        want_temp, want_empty, want_broken = self.temp_var.get(), self.empty_var.get(), self.broken_var.get()
        if not (want_temp or want_empty or want_broken):
            return self.app.notify("Turn on at least one category to scan.", "info")
        age = AGES[self.age_menu.get()]
        if (want_empty or want_broken) and is_protected_root(folder):
            self.app.notify("Folder scans are disabled for drive roots, your user folder and Windows folders. "
                            "Choose a more specific working folder.", "warning")
            want_empty = want_broken = False
            if not want_temp:
                return

        def work():
            found = []
            if want_temp:
                found += scan_user_temp(age)
            if want_empty and folder.is_dir():
                found += scan_empty_folders(folder)
            if want_broken and folder.is_dir():
                found += scan_broken_shortcuts(folder)
            return found

        self._scanning = True
        self.scan_btn.configure(text="Scanning...", state="disabled")
        self.app.set_busy(True, "Scanning for junk...")
        self.run_async(work, self._scan_done)

    def _scan_done(self, result, error):
        self._scanning = False
        self.scan_btn.configure(text="Scan for junk", state="normal")
        self.app.set_busy(False)
        if error:
            return self.app.notify(f"Scan failed: {error}", "error")
        self._dirty = False
        self.items = result
        self._render()
        total = sum(i["size_bytes"] for i in self.items)
        self.app.log(f"Junk scan found {len(self.items)} items ({format_size(total)}).", "info")
        if not self.items:
            self.app.notify("Nothing to clean - your system looks tidy.", "success")

    # ---------------------------------------------------------------- table
    def _render(self):
        self.table.clear()
        for idx, it in enumerate(self.items):
            where = it["detail"] or str(it["path"].parent if it["category"] != "Empty folder" else it["path"])
            self.table.insert((CHECKED if it["selected"] else UNCHECKED, it["name"], it["category"],
                               it["size_formatted"], where), iid=str(idx))
        if self.items:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        self._update_stats()

    def _update_stats(self):
        selected = [i for i in self.items if i["selected"]]
        size = sum(i["size_bytes"] for i in selected)
        if self.items:
            self.t_found.set(len(self.items))
            self.t_sel.set(len(selected))
            self.t_size.set(format_size(size), "success" if size else "neutral")
        else:
            for t in (self.t_found, self.t_sel, self.t_size):
                t.set("-")
        self.clean_btn.configure(state="normal" if selected else "disabled",
                                 text=f"Clean {len(selected)} item{'s' if len(selected) != 1 else ''}" if selected else "Clean selected")
        recycle = config.get("use_recycle_bin", True)
        has_recyclable = any(i["category"] in RECYCLABLE for i in selected)
        if selected and has_recyclable:
            self.note_lbl.configure(text="Empty folders and shortcuts go to the Recycle Bin." if recycle
                                    else "Recycle Bin is off - everything is deleted permanently.")
        else:
            self.note_lbl.configure(text="")

    def _on_click(self, event):
        tree = self.table.tree
        if tree.identify_region(event.x, event.y) != "cell" or tree.identify_column(event.x) != "#1":
            return
        iid = tree.identify_row(event.y)
        if iid.isdigit() and int(iid) < len(self.items):
            item = self.items[int(iid)]
            item["selected"] = not item["selected"]
            self.table.set_cell(iid, "sel", CHECKED if item["selected"] else UNCHECKED)
            self._update_stats()
            return "break"

    def _select(self, value):
        for it in self.items:
            it["selected"] = value
        self._render()

    # ---------------------------------------------------------------- clean
    def clean_selected(self):
        todo = [i for i in self.items if i["selected"]]
        if not todo:
            return
        size = sum(i["size_bytes"] for i in todo)
        recycle = config.get("use_recycle_bin", True)
        permanent = [i for i in todo if not (recycle and i["category"] in RECYCLABLE)]
        msg = f"Remove {len(todo)} item(s) ({format_size(size)})?"
        if permanent:
            msg += f"\n\n{len(permanent)} will be deleted permanently."
        if len(permanent) < len(todo):
            msg += f"\n{len(todo) - len(permanent)} will be moved to the Recycle Bin."
        msg += "\n\nFiles that are in use are skipped automatically."
        if not messagebox.askyesno("Confirm cleanup", msg, icon="warning", parent=self.toplevel):
            return

        self.app.set_busy(True, "Cleaning...")
        self.clean_btn.configure(state="disabled")
        self.run_async(lambda: execute_clean(todo, use_recycle_bin=recycle), self._clean_done)

    def _clean_done(self, res, error):
        self.app.set_busy(False)
        if error:
            self._update_stats()
            return self.app.notify(f"Cleanup failed: {error}", "error")
        text = f"Removed {res['cleaned']} item{'s' if res['cleaned'] != 1 else ''}, freed {res['freed_formatted']}."
        if res["skipped"]:
            text += f" {res['skipped']} skipped (in use or already gone)."
        for name, reason in res["failed"][:20]:
            self.app.log(f"Skipped {name}: {reason}", "warning")
        self.app.notify(text, "success" if res["cleaned"] else "warning")
        self.app.refresh_drive_space()
        self.start_scan()
