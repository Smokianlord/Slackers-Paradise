import threading

import customtkinter as ctk

from ui import theme as T
from ui import widgets as W


class BaseView(ctk.CTkFrame):
    """A tool page: title header + body. Subclasses implement build() and refresh()."""

    key = ""
    title = ""
    subtitle = ""

    def __init__(self, master, app, detached: bool = False):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.detached = detached
        self._dirty = True

        header = W.transparent(self)
        header.pack(fill="x", padx=28, pady=(22, 16))
        titles = W.transparent(header)
        titles.pack(side="left")
        W.label(titles, self.title, 24, T.TEXT_STRONG, "semi", anchor="w").pack(anchor="w")
        W.label(titles, self.subtitle, 13, T.MUTED, anchor="w", justify="left").pack(anchor="w", pady=(2, 0))

        self.header_actions = W.transparent(header)
        self.header_actions.pack(side="right")
        if not detached:
            W.button(self.header_actions, "Pop out", lambda: app.detach_view(self.key), kind="ghost",
                     width=84, height=32).pack(side="right")

        self.body = W.transparent(self)
        self.body.pack(fill="both", expand=True, padx=28, pady=(0, 22))
        self.build(self.body)

        app.register_view(self)
        self.bind("<Destroy>", self._on_destroy, add="+")

    # -- to override ---------------------------------------------------------
    def build(self, body):
        raise NotImplementedError

    def refresh(self):
        """Called when the view becomes visible and its data is stale."""

    # -- plumbing ----------------------------------------------------------------
    def _on_destroy(self, event):
        if event.widget is self:
            self.app.unregister_view(self)

    def on_folder_changed(self, _folder: str):
        self._dirty = True
        if self.winfo_ismapped():
            self.on_show()

    def on_show(self):
        if self._dirty:
            self._dirty = False
            self.refresh()

    def run_async(self, work, done):
        """Run `work()` on a worker thread; call `done(result, error)` on the UI thread."""
        box = {}

        def target():
            try:
                box["result"] = work()
            except Exception as exc:  # reported to the caller
                box["error"] = exc

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        def poll():
            try:
                if not self.winfo_exists():
                    return
                if thread.is_alive():
                    self.after(40, poll)
                else:
                    done(box.get("result"), box.get("error"))
            except Exception:
                pass

        poll()

    @property
    def toplevel(self):
        return self.winfo_toplevel()
