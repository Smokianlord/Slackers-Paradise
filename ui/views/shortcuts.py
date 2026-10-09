import os
import queue
from pathlib import Path
from tkinter import filedialog, messagebox

from core.config import config
from core.shortcuts import scan_shortcuts, shortcut_runner
from ui import theme as T
from ui import widgets as W
from ui.base import BaseView

DELAYS = {"No delay": 0, "0.25 s": 250, "0.5 s (recommended)": 500, "1 s": 1000, "2 s": 2000, "5 s": 5000}
CHECKED, UNCHECKED = "●", "○"


class ShortcutExecutorView(BaseView):
    key = "shortcuts"
    title = "ShortcutExecutor"
    subtitle = "Launch many shortcuts at once - staggered so your PC never freezes."

    def build(self, body):
        self.shortcuts = []
        self._events = queue.Queue()
        self._running = False

        # --- locations ------------------------------------------------------------
        loc = W.Card(body)
        loc.pack(fill="x", pady=(0, 12))
        row = W.transparent(loc)
        row.pack(fill="x", padx=18, pady=14)
        W.label(row, "Jump to", 12, T.MUTED).pack(side="left", padx=(0, 10))
        W.button(row, "Shortcut library", self._go_library, kind="soft", width=130, height=32).pack(side="left", padx=(0, 6))
        W.button(row, "Desktop", lambda: self._go(Path.home() / "Desktop"), kind="secondary", width=86, height=32).pack(side="left", padx=(0, 6))
        W.button(row, "Downloads", lambda: self._go(Path.home() / "Downloads"), kind="secondary", width=100, height=32).pack(side="left", padx=(0, 14))
        self.library_lbl = W.label(row, "", 12, T.MUTED)
        self.library_lbl.pack(side="left")
        W.button(row, "Set library folder...", self._set_library, kind="ghost", width=150, height=32).pack(side="right")

        # --- list --------------------------------------------------------------------
        card = W.Card(body)
        card.pack(fill="both", expand=True)
        bar = W.transparent(card)
        bar.pack(fill="x", padx=18, pady=(14, 8))
        self.search = W.entry(bar, "Search shortcuts...", width=260, height=34)
        self.search.pack(side="left", padx=(0, 10))
        self.search.bind("<KeyRelease>", lambda _e: self._render())
        W.button(bar, "Select all", lambda: self._select(True), kind="secondary", width=90, height=34).pack(side="left", padx=(0, 6))
        W.button(bar, "None", lambda: self._select(False), kind="secondary", width=64, height=34).pack(side="left", padx=(0, 6))
        W.button(bar, "Rescan", self.refresh, kind="ghost", width=76, height=34).pack(side="left")
        self.delay_menu = W.option_menu(bar, list(DELAYS), width=190, height=34)
        self.delay_menu.pack(side="right")
        current = config.get("shortcut_delay_ms", 500)
        self.delay_menu.set(next((k for k, v in DELAYS.items() if v == current), "0.5 s (recommended)"))
        W.label(bar, "Delay between launches", 12, T.MUTED).pack(side="right", padx=(0, 8))

        foot = W.transparent(card)
        foot.pack(side="bottom", fill="x", padx=18, pady=(0, 16))
        holder = W.transparent(card)
        holder.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.table = W.DataTable(holder, [
            {"id": "sel", "title": "", "width": 44, "anchor": "center", "sort": False},
            {"id": "name", "title": "Name", "width": 250, "stretch": True},
            {"id": "type", "title": "Type", "width": 70, "anchor": "center"},
            {"id": "status", "title": "Target", "width": 80, "anchor": "center"},
            {"id": "target", "title": "Opens", "width": 420, "stretch": True},
        ], on_click=self._on_click, on_double_click=self._on_double)
        self.table.pack(fill="both", expand=True)
        self.table.tone_tag("s_ok", T.TEXT)
        self.table.tone_tag("s_missing", T.DANGER)
        self.empty = W.EmptyState(holder, "shortcuts", "No shortcuts here",
                                  "This folder has no .lnk, .url, .bat, .cmd or .exe files.\nPick another folder from 'Jump to' above.")

        self.status_lbl = W.label(foot, "", 13, T.MUTED)
        self.status_lbl.pack(side="left")
        self.progress = ctk_progress(foot)
        self.progress.pack(side="left", padx=16)
        self.launch_btn = W.button(foot, "Launch selected", self.launch_selected, kind="primary", width=170, height=40)
        self.launch_btn.pack(side="right")
        self.stop_btn = W.button(foot, "Stop", self.abort_launch, kind="danger", width=80, height=40, state="disabled")
        self.stop_btn.pack(side="right", padx=(0, 8))
        self._update_library_label()

    # ------------------------------------------------------------- locations
    def _library(self) -> str:
        return config.get("shortcut_folder", "") or ""

    def _update_library_label(self):
        lib = self._library()
        short = lib if len(lib) <= 46 else lib[:20] + "..." + lib[-23:]
        self.library_lbl.configure(text=short or "No library folder set")

    def _go(self, folder):
        folder = str(folder)
        if os.path.isdir(folder):
            self.app.set_active_folder(folder)
        else:
            self.app.notify(f"Folder not found: {folder}", "warning")

    def _go_library(self):
        lib = self._library()
        if lib and os.path.isdir(lib):
            self._go(lib)
        else:
            self._set_library()

    def _set_library(self):
        initial = self._library() if os.path.isdir(self._library()) else self.app.get_active_folder()
        chosen = filedialog.askdirectory(parent=self.toplevel, initialdir=initial, title="Choose your shortcut library folder")
        if chosen:
            config.set("shortcut_folder", os.path.abspath(chosen))
            self._update_library_label()
            self._go(chosen)

    # ------------------------------------------------------------------ list
    def refresh(self):
        folder = Path(self.app.get_active_folder())
        previously = {s["filename"]: s["selected"] for s in self.shortcuts}
        self.shortcuts = scan_shortcuts(folder)
        for s in self.shortcuts:
            s["selected"] = previously.get(s["filename"], True)
        self._render()

    def _render(self):
        q = self.search.get().strip().lower()
        self.table.clear()
        shown = 0
        for s in self.shortcuts:
            if q and q not in s["name"].lower() and q not in s["target"].lower():
                continue
            missing = not s["is_valid"]
            self.table.insert(
                (CHECKED if s["selected"] else UNCHECKED, s["name"], s["type"], "Missing" if missing else "OK", s["target"]),
                tags=("s_missing" if missing else "s_ok",), iid=s["filename"])
            shown += 1
        if shown:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        if not self._running:
            self._update_status()

    def _update_status(self):
        selected = sum(1 for s in self.shortcuts if s["selected"])
        self.status_lbl.configure(text=f"{len(self.shortcuts)} shortcuts  ·  {selected} selected", text_color=T.MUTED)
        self.launch_btn.configure(state="normal" if selected else "disabled",
                                  text=f"Launch {selected}" if selected else "Launch selected")

    def _find(self, filename):
        return next((s for s in self.shortcuts if s["filename"] == filename), None)

    def _on_click(self, event):
        tree = self.table.tree
        if tree.identify_region(event.x, event.y) != "cell" or tree.identify_column(event.x) != "#1":
            return
        sc = self._find(tree.identify_row(event.y))
        if sc:
            sc["selected"] = not sc["selected"]
            self.table.set_cell(sc["filename"], "sel", CHECKED if sc["selected"] else UNCHECKED)
            self._update_status()
            return "break"

    def _on_double(self, event):
        tree = self.table.tree
        if tree.identify_region(event.x, event.y) != "cell" or tree.identify_column(event.x) == "#1":
            return
        sc = self._find(tree.identify_row(event.y))
        if sc:
            try:
                os.startfile(str(sc["path"]))
                self.app.log(f"Launched {sc['name']}.", "info")
            except OSError as exc:
                self.app.notify(f"Could not launch {sc['name']}: {exc}", "error")

    def _select(self, value):
        for s in self.shortcuts:
            s["selected"] = value
        self._render()

    # ---------------------------------------------------------------- launch
    def launch_selected(self):
        selected = [s for s in self.shortcuts if s["selected"]]
        if not selected or self._running:
            return
        delay = DELAYS.get(self.delay_menu.get(), 500)
        config.set("shortcut_delay_ms", delay)
        if config.get("confirm_destructive", True) and len(selected) > 1:
            if not messagebox.askyesno("Confirm launch", f"Launch {len(selected)} shortcuts from:\n\n{self.app.get_active_folder()}",
                                       parent=self.toplevel):
                return

        self._running = True
        self.launch_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)
        self.app.set_busy(True, "Launching shortcuts...")
        started = shortcut_runner.launch_staggered(
            selected, delay_ms=delay,
            on_progress=lambda i, n, name: self._events.put(("progress", i, n, name)),
            on_complete=lambda ok, failed, aborted: self._events.put(("done", ok, failed, aborted)))
        if not started:
            self._finish(0, [], False)
            return self.app.notify("A launch is already in progress.", "warning")
        self._poll()

    def _poll(self):
        try:
            while True:
                event = self._events.get_nowait()
                if event[0] == "progress":
                    _, i, n, name = event
                    self.progress.set(i / n)
                    self.status_lbl.configure(text=f"Launching {i} of {n}:  {name}", text_color=T.TEXT)
                    self.app.log(f"Launching {name}", "info")
                else:
                    _, ok, failed, aborted = event
                    return self._finish(ok, failed, aborted)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(60, self._poll)

    def _finish(self, launched, failed, aborted):
        self._running = False
        self.stop_btn.configure(state="disabled")
        self.app.set_busy(False)
        self.progress.set(0 if aborted else 1)
        text = f"{'Stopped after' if aborted else 'Launched'} {launched} shortcut{'s' if launched != 1 else ''}"
        if failed:
            text += f", {len(failed)} failed"
            for name, reason in failed[:20]:
                self.app.log(f"Could not launch {name}: {reason}", "error")
        self.app.notify(text + ".", "warning" if (failed or aborted) else "success")
        self._update_status()

    def abort_launch(self):
        shortcut_runner.abort()
        self.stop_btn.configure(state="disabled")
        self.status_lbl.configure(text="Stopping...")


def ctk_progress(master):
    import customtkinter as ctk
    bar = ctk.CTkProgressBar(master, width=200, height=8, progress_color=T.ACCENT, fg_color=T.SURFACE_ALT)
    bar.set(0)
    return bar
