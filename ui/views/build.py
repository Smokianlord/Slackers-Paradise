import re
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.builder import (
    apply_suggestions, execute_create_folders, preview_creation, undo_created_folders,
)
from core.config import config
from ui import theme as T
from ui import widgets as W
from ui.base import BaseView

SEQ_RE = re.compile(r"\{(?:\d+|[A-Za-z])\.\.(?:\d+|[A-Za-z])\}")
STATUS_LABEL = {"new": "Ready", "existing": "Exists", "fixable": "Needs fix", "invalid": "Invalid", "duplicate": "Duplicate"}
TEMPLATE_PLACEHOLDER = "Templates"
SAVE_TEMPLATE = "Save current list as template..."


class BuildFolderView(BaseView):
    key = "build"
    title = "Build-a-Folder"
    subtitle = "Create folders in bulk. One folder per line - commas are kept as part of the name."

    def build(self, body):
        self._after_id = None
        self._items = {}
        self._last_created = []

        body.grid_columnconfigure(0, weight=4, uniform="cols")
        body.grid_columnconfigure(1, weight=5, uniform="cols")
        body.grid_rowconfigure(0, weight=1)

        self._build_input(W.Card(body))
        self.input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_preview(W.Card(body))
        self.preview_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._schedule_preview(0)

    # ------------------------------------------------------------------ input
    def _build_input(self, card):
        self.input_card = card
        head = W.transparent(card)
        head.pack(fill="x", padx=18, pady=(16, 10))
        W.section_title(head, "Folder names", "One folder per line").pack(side="left")

        tools = W.transparent(head)
        tools.pack(side="right")
        self.template_menu = W.option_menu(tools, [TEMPLATE_PLACEHOLDER], width=130, height=32, command=self._on_template)
        self.template_menu.pack(side="left", padx=(0, 6))
        W.button(tools, "Import", self._import_file, kind="secondary", width=70, height=32).pack(side="left")
        self._refresh_template_menu()

        opts = W.transparent(card)
        opts.pack(side="bottom", fill="x", padx=18, pady=(0, 16))
        seq = W.transparent(card)
        seq.pack(side="bottom", fill="x", padx=18, pady=(0, 10))

        self.textbox = W.textbox(card, wrap="word")
        self.textbox.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        for event_name in ("<KeyRelease>", "<<Paste>>", "<<Cut>>", "<FocusOut>"):
            self.textbox.bind(event_name, lambda _e: self._schedule_preview())
        # Tk's Text widget treats Ctrl+O as "insert newline"; the app uses it for Browse
        self.textbox.bind("<Control-o>", lambda _e: (self.app.browse_folder(), "break")[1])

        W.label(seq, "Sequence", 12, T.MUTED).pack(side="left", padx=(0, 8))
        self.seq_entry = W.entry(seq, "Episode_{01..12}", width=100, height=32)
        self.seq_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.seq_entry.bind("<Return>", lambda _e: self._add_sequence())
        W.button(seq, "Add", self._add_sequence, kind="secondary", width=64, height=32).pack(side="left")

        self.nested_var = ctk.BooleanVar(value=config.get("nested_paths", True))
        W.switch(opts, "Slash creates sub-folders (src/utils)", self.nested_var, self._on_options).pack(side="left")
        self.open_var = ctk.BooleanVar(value=config.get("auto_open_after_create", False))
        W.switch(opts, "Open when done", self.open_var,
                 lambda: config.set("auto_open_after_create", self.open_var.get())).pack(side="right")

    # ---------------------------------------------------------------- preview
    def _build_preview(self, card):
        self.preview_card = card
        tiles = W.transparent(card)
        tiles.pack(fill="x", padx=18, pady=(16, 10))
        for i in range(4):
            tiles.grid_columnconfigure(i, weight=1, uniform="tiles")
        self.t_ready = W.StatTile(tiles, "Ready to create", "0")
        self.t_exist = W.StatTile(tiles, "Already exist", "0")
        self.t_fix = W.StatTile(tiles, "Need a fix", "0")
        self.t_bad = W.StatTile(tiles, "Can't be used", "0")
        for i, tile in enumerate((self.t_ready, self.t_exist, self.t_fix, self.t_bad)):
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))

        self.path_lbl = W.label(card, "", 12, T.MUTED, anchor="w")
        self.path_lbl.pack(fill="x", padx=20, pady=(0, 6))

        bar = W.transparent(card)
        bar.pack(side="bottom", fill="x", padx=18, pady=(0, 16))
        self.detail = ctk.CTkFrame(card, fg_color=T.SURFACE_ALT, corner_radius=T.RADIUS_SM, height=100)
        self.detail.pack(side="bottom", fill="x", padx=18, pady=(0, 12))
        self.detail.pack_propagate(False)
        self.detail.grid_columnconfigure(0, weight=1)
        self.detail_lbl = W.label(self.detail, "Select a line to see why it needs a fix.", 12, T.MUTED,
                                  anchor="nw", justify="left", wraplength=400)
        self.detail_lbl.grid(row=0, column=0, sticky="nsew", padx=14, pady=10)
        self.use_btn = W.button(self.detail, "Use it", self._use_suggestion, kind="soft", width=70, height=30)

        holder = W.transparent(card)
        holder.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.table = W.DataTable(holder, [
            {"id": "line", "title": "Line", "width": 44, "anchor": "center"},
            {"id": "status", "title": "Status", "width": 78},
            {"id": "name", "title": "Folder name", "width": 170, "stretch": True},
            {"id": "fix", "title": "Suggested fix", "width": 170, "stretch": True},
        ], on_select=self._on_row_select)
        self.table.pack(fill="both", expand=True)
        self.table.tone_tag("t_ok", T.TEXT)
        self.table.tone_tag("t_existing", T.MUTED)
        self.table.tone_tag("t_fixable", T.WARNING)
        self.table.tone_tag("t_invalid", T.DANGER)
        self.empty = W.EmptyState(holder, "build", "Nothing to preview yet",
                                  "Type or paste folder names on the left.\nProblems and suggested fixes appear here instantly.")

        self.fix_btn = W.button(bar, "Fix all names", self._apply_all_fixes, kind="soft", width=120)
        self.fix_btn.pack(side="left")
        self.undo_btn = W.button(bar, "Undo last creation", self._undo, kind="ghost", width=140, state="disabled")
        self.undo_btn.pack(side="left", padx=(6, 0))
        self.create_btn = W.button(bar, "Create folders", self.create_folders, kind="primary", width=170, height=40)
        self.create_btn.pack(side="right")

    # ------------------------------------------------------------- templates
    def _refresh_template_menu(self):
        customs = list(config.get("custom_templates", {}).keys())
        values = list(config.all_templates().keys()) + [SAVE_TEMPLATE]
        values += [f"Remove template: {name}" for name in customs]
        self.template_menu.configure(values=values)
        self.template_menu.set(TEMPLATE_PLACEHOLDER)

    def _on_template(self, choice):
        self.template_menu.set(TEMPLATE_PLACEHOLDER)
        if choice == SAVE_TEMPLATE:
            return self._save_template()
        if choice.startswith("Remove template: "):
            name = choice.split(": ", 1)[1]
            if messagebox.askyesno("Remove template", f"Remove your template '{name}'?", parent=self.toplevel):
                config.delete_template(name)
                self._refresh_template_menu()
                self.app.notify(f"Template '{name}' removed.", "info")
            return
        lines = config.all_templates().get(choice)
        if lines:
            current = self._text().strip()
            if current and not messagebox.askyesno("Replace list", f"Replace the current list with the '{choice}' template?",
                                                   parent=self.toplevel):
                return
            self._set_text("\n".join(lines))
            self.app.log(f"Loaded template '{choice}'.", "info")

    def _save_template(self):
        lines = [ln.strip() for ln in self._text().splitlines() if ln.strip()]
        if not lines:
            return self.app.notify("Add some folder names first, then save them as a template.", "warning")
        dialog = ctk.CTkInputDialog(text="Name for this template:", title="Save template")
        name = (dialog.get_input() or "").strip()
        if not name:
            return
        config.save_template(name, lines)
        self._refresh_template_menu()
        self.app.notify(f"Template '{name}' saved ({len(lines)} lines).", "success")

    # ----------------------------------------------------------------- input
    def _text(self) -> str:
        return self.textbox.get("1.0", "end-1c")

    def _set_text(self, text: str):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self._schedule_preview(0)

    def _import_file(self):
        path = filedialog.askopenfilename(
            parent=self.toplevel, title="Import folder names",
            filetypes=[("Text files", "*.txt *.csv *.md"), ("All files", "*.*")])
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            return self.app.notify(f"Could not read file: {exc}", "error")
        existing = self._text().rstrip()
        self._set_text((existing + "\n" if existing else "") + text.strip("\n"))
        self.app.notify(f"Imported {len([l for l in text.splitlines() if l.strip()])} lines from {Path(path).name}.", "success")

    def _add_sequence(self):
        value = self.seq_entry.get().strip()
        if not value:
            return
        existing = self._text().rstrip()
        self._set_text((existing + "\n" if existing else "") + value)
        self.seq_entry.delete(0, "end")

    def _on_options(self):
        config.set("nested_paths", self.nested_var.get())
        self._schedule_preview(0)

    # --------------------------------------------------------------- preview
    def refresh(self):
        self._schedule_preview(0)

    def _schedule_preview(self, delay=220):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(delay, self.preview)

    def _base(self) -> Path:
        return Path(self.app.get_active_folder())

    def preview(self):
        self._after_id = None
        base = self._base()
        self.pv = preview_creation(base, self._text(), nested=self.nested_var.get())
        pv = self.pv

        self.table.clear()
        self._items = {}
        tone_for = {"new": "t_ok", "existing": "t_existing", "fixable": "t_fixable",
                    "invalid": "t_invalid", "duplicate": "t_existing"}
        for idx, item in enumerate(pv["items"]):
            iid = str(idx)
            self._items[iid] = item
            self.table.insert(
                (item["line"], STATUS_LABEL[item["status"]], item["original"], item["suggestion"] or ""),
                tags=(tone_for[item["status"]],), iid=iid)

        if pv["items"]:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

        self.t_ready.set(pv["new"], "success" if pv["new"] else "neutral")
        self.t_exist.set(pv["existing"])
        self.t_fix.set(pv["fixable"], "warning" if pv["fixable"] else "neutral")
        self.t_bad.set(pv["invalid"] + pv["duplicate"], "danger" if pv["invalid"] else "neutral")
        self.path_lbl.configure(text=f"Creating in  {base}")

        if pv.get("error"):
            self.detail_lbl.configure(text=pv["error"], text_color=T.DANGER)
        else:
            self._show_detail(None)

        creatable = pv["new"] + pv["fixable"]
        self.fix_btn.configure(state="normal" if pv["fixable"] else "disabled",
                               text=f"Fix {pv['fixable']} name{'s' if pv['fixable'] != 1 else ''}" if pv["fixable"] else "Fix all names")
        self.create_btn.configure(
            state="normal" if creatable else "disabled",
            text=f"Create {creatable} folder{'s' if creatable != 1 else ''}" if creatable else "Create folders")

    def _on_row_select(self):
        sel = self.table.selection()
        self._show_detail(self._items.get(sel[0]) if sel else None)

    def _show_detail(self, item):
        self.use_btn.grid_forget()
        if item is None:
            self.detail_lbl.configure(text="Select a line to see why it needs a fix.", text_color=T.MUTED)
            return
        self._selected_item = item
        status = item["status"]
        if status in ("fixable", "invalid"):
            text = "\n".join(f"• {p}" for p in item["issues"][:4])
            if item["suggestion"]:
                text += f"\nSuggested:  {item['suggestion']}"
                self.use_btn.grid(row=0, column=1, sticky="ne", padx=(0, 12), pady=10)
            self.detail_lbl.configure(text=text, text_color=T.WARNING if status == "fixable" else T.DANGER)
        elif status == "existing":
            self.detail_lbl.configure(text="This folder already exists and will be skipped.", text_color=T.MUTED)
        elif status == "duplicate":
            self.detail_lbl.configure(text="; ".join(item["issues"]) or "Listed more than once.", text_color=T.MUTED)
        else:
            self.detail_lbl.configure(text="Valid name - ready to create.", text_color=T.SUCCESS)

    # ------------------------------------------------------------------ fixes
    def _use_suggestion(self):
        item = getattr(self, "_selected_item", None)
        if not item or not item["suggestion"]:
            return
        lines = self._text().split("\n")
        idx = item["line"] - 1
        if idx >= len(lines):
            return
        if SEQ_RE.search(lines[idx]):
            return self.app.notify("Sequence names are fixed automatically when the folders are created.", "info")
        lines[idx] = item["suggestion"]
        self._set_text("\n".join(lines))

    def _apply_all_fixes(self):
        text, changed = apply_suggestions(self._text(), self.nested_var.get(), self._base())
        if changed:
            self._set_text(text)
            self.app.notify(f"Fixed {changed} name{'s' if changed != 1 else ''}.", "success")
        else:
            self.app.notify("Names from sequences are fixed automatically when you create them.", "info")

    # ---------------------------------------------------------------- create
    def create_folders(self):
        base = self._base()
        if not base.is_dir():
            return messagebox.showerror("Folder not found", f"The working folder no longer exists:\n\n{base}",
                                        parent=self.toplevel)
        nested = self.nested_var.get()
        pv = preview_creation(base, self._text(), nested)
        if pv.get("error"):
            return self.app.notify(pv["error"], "error")

        apply_fixes = False
        if pv["fixable"]:
            answer = messagebox.askyesnocancel(
                "Some names need a fix",
                f"{pv['fixable']} name(s) contain characters Windows does not allow "
                "(such as : ? \" * | < >).\n\n"
                "Yes  -  create them using the suggested names\n"
                "No   -  skip those and create only the valid ones\n"
                "Cancel  -  go back and edit",
                parent=self.toplevel)
            if answer is None:
                return
            apply_fixes = answer

        res = execute_create_folders(base, self._text(), nested, apply_fixes)
        n = len(res["created"])
        msg = f"Created {n} folder{'s' if n != 1 else ''}"
        if res["skipped"]:
            msg += f", {len(res['skipped'])} already existed"
        if res["failed"]:
            msg += f", {len(res['failed'])} skipped"
        self.app.notify(msg + ".", "success" if n else "warning")
        for name, reason in res["failed"][:20]:
            self.app.log(f"Skipped '{name}': {reason}", "warning")

        if res["created_dirs"]:
            self._last_created = res["created_dirs"]
            self.undo_btn.configure(state="normal")
        self.preview()
        self.app.refresh_drive_space()
        if self.open_var.get() and n:
            self.app.open_current_in_explorer()

    def _undo(self):
        if not self._last_created:
            return
        res = undo_created_folders(self._last_created)
        self._last_created = []
        self.undo_btn.configure(state="disabled")
        msg = f"Removed {res['removed']} folder{'s' if res['removed'] != 1 else ''}."
        if res["kept"]:
            msg += f" {len(res['kept'])} kept because they are no longer empty."
        self.app.notify(msg, "success" if not res["kept"] else "warning")
        self.preview()
