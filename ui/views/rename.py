from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from core.config import config
from core.renamer import renamer_engine
from ui import theme as T
from ui import widgets as W
from ui.base import BaseView

MODES = ["Roulette", "Sequential", "Find & Replace", "Date stamp", "Change case"]
RANDOM_TYPES = {"4 digits": "4_digit", "6 digits": "6_digit", "8 digits": "8_digit",
                "Hex": "hex", "Letters + digits": "alphanumeric", "Short UUID": "uuid"}
DATE_SOURCES = {"Today": "today", "File modified date": "modified"}
DATE_FORMATS = ["YYYY-MM-DD", "YYYYMMDD", "YYYY-MM-DD_HHMM", "DD-MM-YYYY"]
CASES = {"lowercase": "lower", "UPPERCASE": "upper", "Title Case": "title",
         "snake_case": "snake", "kebab-case": "kebab"}
SORTS = {"Name (natural)": "name", "Date modified": "modified", "Size": "size"}
STATUS_LABEL = {"ready": "Ready", "unchanged": "Unchanged", "conflict": "Conflict", "invalid": "Invalid"}


class RenameRouletteView(BaseView):
    key = "rename"
    title = "RenameRoulette"
    subtitle = "Batch-rename files safely. Every change is previewed first and can be undone."

    def build(self, body):
        self.plan = None
        self._after_id = None
        self.w = {}   # option widgets of the current mode

        # --- configuration card ---------------------------------------------
        cfg = W.Card(body)
        cfg.pack(fill="x", pady=(0, 12))
        top = W.transparent(cfg)
        top.pack(fill="x", padx=18, pady=(16, 8))
        self.mode_seg = W.segmented(top, MODES, command=self._on_mode)
        self.mode_seg.pack(side="left")
        self.mode_seg.set(MODES[0])
        W.button(top, "Refresh preview", lambda: self.generate_preview(), kind="secondary", width=140, height=36).pack(side="right")

        self.opts = W.transparent(cfg)
        self.opts.pack(fill="x", padx=18, pady=(4, 8))

        W.divider(cfg).pack(fill="x", padx=18, pady=(4, 10))
        common = W.transparent(cfg)
        common.pack(fill="x", padx=18, pady=(0, 14))
        self.filter_entry = self._field(common, "Only these file types", lambda p: W.entry(p, "*  or  .jpg; .png", width=190))
        self.filter_entry.insert(0, "*")
        self.sort_menu = self._field(common, "Process in order of", lambda p: W.option_menu(p, list(SORTS), width=170, command=lambda _v: self._schedule()))
        self.hidden_var = ctk.BooleanVar(value=False)
        W.switch(common, "Include hidden files", self.hidden_var, self._schedule).pack(side="left", pady=(18, 0), padx=(4, 0))
        self.filter_entry.bind("<KeyRelease>", lambda _e: self._schedule())

        self._build_mode_options()

        # --- preview table ----------------------------------------------------
        card = W.Card(body)
        card.pack(fill="both", expand=True)
        foot = W.transparent(card)
        foot.pack(side="bottom", fill="x", padx=18, pady=(0, 16))
        holder = W.transparent(card)
        holder.pack(fill="both", expand=True, padx=18, pady=(16, 8))
        self.table = W.DataTable(holder, [
            {"id": "old", "title": "Current name", "width": 280, "stretch": True},
            {"id": "new", "title": "New name", "width": 280, "stretch": True},
            {"id": "status", "title": "Status", "width": 90, "anchor": "center"},
            {"id": "note", "title": "Note", "width": 240, "stretch": True},
        ])
        self.table.pack(fill="both", expand=True)
        self.table.tone_tag("r_ready", T.TEXT)
        self.table.tone_tag("r_unchanged", T.FAINT)
        self.table.tone_tag("r_conflict", T.WARNING)
        self.table.tone_tag("r_invalid", T.DANGER)
        self.empty = W.EmptyState(holder, "rename", "No files to rename",
                                  "Pick a working folder that contains files,\nor widen the file-type filter.")

        self.stats_lbl = W.label(foot, "", 13, T.MUTED)
        self.stats_lbl.pack(side="left")
        self.rename_btn = W.button(foot, "Rename files", self.execute_rename, kind="primary", width=170, height=40)
        self.rename_btn.pack(side="right")
        self.undo_btn = W.button(foot, "Undo last rename", self.undo_rename, kind="secondary", width=160, height=40)
        self.undo_btn.pack(side="right", padx=(0, 8))
        self._update_undo()

    # --------------------------------------------------------------- options
    def _field(self, parent, caption, factory):
        box = W.transparent(parent)
        box.pack(side="left", padx=(0, 12))
        W.label(box, caption, 11, T.MUTED, anchor="w").pack(anchor="w", pady=(0, 3))
        widget = factory(box)
        widget.pack(anchor="w")
        return widget

    def _build_mode_options(self):
        for child in self.opts.winfo_children():
            child.destroy()
        self.w = {}
        mode = self.mode_seg.get()
        row = W.transparent(self.opts)
        row.pack(fill="x")
        entry_kw = lambda p, ph="", width=130: W.entry(p, ph, width=width)  # noqa: E731

        def typed(key, caption, factory):
            self.w[key] = self._field(row, caption, factory)
            if isinstance(self.w[key], ctk.CTkEntry):
                self.w[key].bind("<KeyRelease>", lambda _e: self._schedule())

        if mode == "Roulette":
            typed("rtype", "Random name style", lambda p: W.option_menu(p, list(RANDOM_TYPES), width=170, command=lambda _v: self._schedule()))
            W.label(row, "Every file gets a unique random name. Great for anonymising a folder.", 12, T.MUTED).pack(side="left", pady=(18, 0))
        elif mode == "Sequential":
            typed("prefix", "Prefix", lambda p: entry_kw(p, "Item_", 140))
            self.w["prefix"].insert(0, "Item_")
            typed("start", "Start at", lambda p: entry_kw(p, "1", 70))
            self.w["start"].insert(0, "1")
            typed("pad", "Digits", lambda p: W.option_menu(p, ["1", "2", "3", "4", "5", "6"], width=80, command=lambda _v: self._schedule()))
            self.w["pad"].set("3")
            typed("suffix", "Suffix", lambda p: entry_kw(p, "", 110))
        elif mode == "Find & Replace":
            typed("find", "Find", lambda p: entry_kw(p, "text to find", 150))
            typed("repl", "Replace with", lambda p: entry_kw(p, "replacement", 150))
            typed("addp", "Add prefix", lambda p: entry_kw(p, "", 110))
            typed("adds", "Add suffix", lambda p: entry_kw(p, "", 110))
            sw = W.transparent(row)
            sw.pack(side="left", pady=(18, 0))
            self.w["case_var"] = ctk.BooleanVar(value=False)
            self.w["regex_var"] = ctk.BooleanVar(value=False)
            W.switch(sw, "Match case", self.w["case_var"], self._schedule).pack(side="left", padx=(0, 12))
            W.switch(sw, "Regex", self.w["regex_var"], self._schedule).pack(side="left")
        elif mode == "Date stamp":
            typed("dsrc", "Date from", lambda p: W.option_menu(p, list(DATE_SOURCES), width=170, command=lambda _v: self._schedule()))
            typed("dfmt", "Format", lambda p: W.option_menu(p, DATE_FORMATS, width=170, command=lambda _v: self._schedule()))
            typed("dpos", "Placed", lambda p: W.option_menu(p, ["Before name", "After name"], width=140, command=lambda _v: self._schedule()))
        elif mode == "Change case":
            typed("case", "Convert names to", lambda p: W.option_menu(p, list(CASES), width=170, command=lambda _v: self._schedule()))

    def _collect(self):
        mode = self.mode_seg.get()
        w = self.w
        kw = {}
        if mode == "Roulette":
            kw = {"mode": "roulette", "random_type": RANDOM_TYPES[w["rtype"].get()]}
        elif mode == "Sequential":
            try:
                start = int(w["start"].get())
            except ValueError:
                start = 1
            kw = {"mode": "sequential", "seq_prefix": w["prefix"].get(), "seq_start": start,
                  "seq_padding": int(w["pad"].get()), "seq_suffix": w["suffix"].get()}
        elif mode == "Find & Replace":
            kw = {"mode": "find_replace", "find_text": w["find"].get(), "replace_text": w["repl"].get(),
                  "add_prefix": w["addp"].get(), "add_suffix": w["adds"].get(),
                  "case_sensitive": w["case_var"].get(), "use_regex": w["regex_var"].get()}
        elif mode == "Date stamp":
            kw = {"mode": "date_stamp", "date_source": DATE_SOURCES[w["dsrc"].get()], "date_format": w["dfmt"].get(),
                  "date_placement": "prefix" if w["dpos"].get() == "Before name" else "suffix"}
        else:
            kw = {"mode": "case", "case_mode": CASES[w["case"].get()]}
        kw["extension_filter"] = self.filter_entry.get().strip() or "*"
        kw["include_hidden"] = self.hidden_var.get()
        kw["sort_by"] = SORTS[self.sort_menu.get()]
        return kw

    def _on_mode(self, _value):
        self._build_mode_options()
        self.generate_preview()

    # --------------------------------------------------------------- preview
    def refresh(self):
        self.generate_preview()

    def _schedule(self, delay=250):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(delay, self.generate_preview)

    def generate_preview(self):
        self._after_id = None
        folder = Path(self.app.get_active_folder())
        self.table.clear()
        self.plan = None
        if not folder.is_dir():
            self.stats_lbl.configure(text="Working folder not found.")
            self._update_buttons()
            return
        try:
            self.plan = renamer_engine.generate_plan(folder, **self._collect())
        except ValueError as exc:
            self.stats_lbl.configure(text=str(exc), text_color=T.DANGER)
            self.empty.place_forget()
            self._update_buttons()
            return

        tone = {"ready": "r_ready", "unchanged": "r_unchanged", "conflict": "r_conflict", "invalid": "r_invalid"}
        for it in self.plan["items"]:
            self.table.insert((it["old_name"], it["new_name"], STATUS_LABEL[it["status"]], it["message"]),
                              tags=(tone[it["status"]],))
        if self.plan["items"]:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

        p = self.plan
        parts = [f"{p['ready']} ready"]
        if p["unchanged"]:
            parts.append(f"{p['unchanged']} unchanged")
        if p["conflicts"]:
            parts.append(f"{p['conflicts']} conflict{'s' if p['conflicts'] != 1 else ''}")
        if p["invalid"]:
            parts.append(f"{p['invalid']} invalid")
        problem = bool(p["conflicts"] or p["invalid"])
        self.stats_lbl.configure(text="  ·  ".join(parts), text_color=T.WARNING if problem else T.MUTED)
        self._update_buttons()

    def _update_buttons(self):
        ready = self.plan["ready"] if self.plan else 0
        self.rename_btn.configure(state="normal" if ready else "disabled",
                                  text=f"Rename {ready} file{'s' if ready != 1 else ''}" if ready else "Rename files")

    def _update_undo(self):
        n = len(renamer_engine.undo_stack)
        self.undo_btn.configure(state="normal" if n else "disabled", text=f"Undo last rename ({n})" if n else "Undo last rename")

    # --------------------------------------------------------------- execute
    def execute_rename(self):
        if not self.plan or not self.plan["ready"]:
            return
        p = self.plan
        skipped = p["conflicts"] + p["invalid"]
        if config.get("confirm_destructive", True):
            msg = f"Rename {p['ready']} file(s) in:\n\n{p['folder']}\n\n"
            if skipped:
                msg += f"{skipped} item(s) with conflicts or invalid names will be skipped.\n\n"
            msg += "You can undo this afterwards."
            if not messagebox.askyesno("Confirm rename", msg, parent=self.toplevel):
                return

        res = renamer_engine.execute_rename(p)
        n, failed = res["renamed"], res["failed"]
        text = f"Renamed {n} file{'s' if n != 1 else ''}"
        if failed:
            text += f", {len(failed)} failed"
            for name, reason in failed[:20]:
                self.app.log(f"Could not rename {name}: {reason}", "error")
        self.app.notify(text + ".", "success" if n and not failed else "warning")
        self._update_undo()
        self.generate_preview()

    def undo_rename(self):
        res = renamer_engine.undo_last_rename()
        if res["restored"]:
            text = f"Restored {res['restored']} file name{'s' if res['restored'] != 1 else ''}."
            if res["failed"]:
                text += f" {len(res['failed'])} could not be restored."
                for name, reason in res["failed"][:20]:
                    self.app.log(f"Undo problem for {name}: {reason}", "warning")
            self.app.notify(text, "success" if not res["failed"] else "warning")
        else:
            self.app.notify("Nothing could be restored.", "warning")
        self._update_undo()
        self.generate_preview()
