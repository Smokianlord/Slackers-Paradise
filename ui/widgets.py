"""Reusable, consistently styled building blocks."""
import re
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Sequence

import customtkinter as ctk

from ui import theme as T

ZEBRA = ("#F9F8FE", "#18172F")

TONES = {
    # tone: (text color, soft background)
    "neutral": (T.MUTED, T.SURFACE_ALT),
    "accent": (T.ACCENT, T.ACCENT_SOFT),
    "success": (T.SUCCESS, T.SUCCESS_SOFT),
    "warning": (T.WARNING, T.WARNING_SOFT),
    "danger": (T.DANGER, T.DANGER_SOFT),
    "info": (T.INFO, T.INFO_SOFT),
}


# --------------------------------------------------------------------- basics
def label(master, text="", size=13, color=T.TEXT, weight="normal", **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=text, font=T.font(size, weight), text_color=color, **kw)


def icon(master, name: str, size=16, color=T.MUTED, **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=T.ICONS[name], font=T.icon_font(size), text_color=color, width=size + 4, **kw)


class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", T.SURFACE)
        kw.setdefault("border_color", T.BORDER)
        kw.setdefault("border_width", 1)
        kw.setdefault("corner_radius", T.RADIUS)
        super().__init__(master, **kw)


def transparent(master, **kw) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color="transparent", **kw)


_BUTTON_STYLES = {
    "primary": dict(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color=T.ON_ACCENT, border_width=0),
    "secondary": dict(fg_color=T.SURFACE_ALT, hover_color=T.SURFACE_HOVER, text_color=T.TEXT,
                      border_width=1, border_color=T.BORDER),
    "soft": dict(fg_color=T.ACCENT_SOFT, hover_color=T.SURFACE_HOVER, text_color=T.ACCENT, border_width=0),
    "ghost": dict(fg_color="transparent", hover_color=T.SURFACE_ALT, text_color=T.MUTED, border_width=0),
    "danger": dict(fg_color=T.DANGER_FILL, hover_color=T.DANGER_FILL_HOVER, text_color=T.ON_ACCENT, border_width=0),
}


# Darker "edge" colour shown under a raised button
_LIPS = {
    "primary": ("#4328B8", "#4A33B8"),
    "danger": ("#8A1638", "#8A1F3F"),
    "secondary": ("#C9C3E4", "#0B0A1A"),
    "soft": ("#C2B6EE", "#140F33"),
}
_LIP_DISABLED = ("#DAD6EC", "#0F0E20")
LIP = 4


class Button3D(ctk.CTkFrame):
    """A raised key-cap style button: face + darker lip underneath that it sinks into when pressed."""

    def __init__(self, master, kind, **btn_kw):
        lip = _LIPS.get(kind)
        # Transparent container: no coloured box behind the rounded button corners
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self._kind = kind
        self._raised = lip is not None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.lip = None
        if self._raised:
            # the "edge": a rounded slab sitting LIP px lower than the face, drawn first (below)
            self.lip = ctk.CTkFrame(self, width=1, height=1, fg_color=lip, corner_radius=T.RADIUS_SM, border_width=0)
            self.lip.grid(row=0, column=0, sticky="nsew", pady=(LIP, 0))
        self.btn = ctk.CTkButton(self, **btn_kw)
        self.btn.grid(row=0, column=0, sticky="nsew", pady=(0, LIP) if self._raised else 0)
        if self._raised:
            self.btn.bind("<ButtonPress-1>", self._press, add="+")
            self.btn.bind("<ButtonRelease-1>", self._release, add="+")

    def _press(self, _e):
        if self.btn.cget("state") != "disabled":
            self.btn.grid_configure(pady=(LIP - 1, 1))

    def _release(self, _e):
        self.btn.grid_configure(pady=(0, LIP))

    def configure(self, **kw):
        state = kw.pop("state", None)
        if kw:
            self.btn.configure(**kw)
        if state is None:
            return
        style = _BUTTON_STYLES[self._kind]
        if state == "disabled" and self._kind in ("primary", "danger", "soft"):
            self.btn.configure(state="disabled", fg_color=T.SURFACE_ALT, hover_color=T.SURFACE_ALT)
            self.lip.configure(fg_color=_LIP_DISABLED)
        else:
            self.btn.configure(state=state, fg_color=style["fg_color"], hover_color=style["hover_color"])
            if self._raised:
                self.lip.configure(fg_color=_LIPS[self._kind])

    def invoke(self):
        return self.btn.invoke()


def button(master, text, command=None, kind="secondary", width=0, height=36, **kw) -> Button3D:
    style = dict(_BUTTON_STYLES[kind])
    style["font"] = T.font(13, "semi" if kind in ("primary", "danger") else "normal")
    style.update(kw)
    disabled = style.get("state") == "disabled"
    widget = Button3D(master, kind, text=text, command=command, width=width, height=height,
                      corner_radius=T.RADIUS_SM, text_color_disabled=T.FAINT, **style)
    if disabled:
        set_enabled(widget, False)
    return widget


def set_enabled(btn, enabled: bool):
    """Enable/disable a button and make the disabled state look disabled (not just dimmed text)."""
    btn.configure(state="normal" if enabled else "disabled")


def icon_button(master, name, command=None, size=34, **kw) -> ctk.CTkButton:
    style = dict(_BUTTON_STYLES["ghost"])
    style.update(kw)
    return ctk.CTkButton(
        master, text=T.ICONS[name], command=command, width=size, height=size,
        corner_radius=T.RADIUS_SM, font=T.icon_font(15), **style,
    )


def entry(master, placeholder="", width=200, height=36, **kw) -> ctk.CTkEntry:
    return ctk.CTkEntry(
        master, placeholder_text=placeholder, width=width, height=height, corner_radius=T.RADIUS_SM,
        fg_color=T.SURFACE_ALT, border_color=T.BORDER, border_width=1, text_color=T.TEXT,
        placeholder_text_color=T.FAINT, font=T.font(13), **kw,
    )


def option_menu(master, values, width=160, height=36, command=None, **kw) -> ctk.CTkOptionMenu:
    return ctk.CTkOptionMenu(
        master, values=values, width=width, height=height, command=command, corner_radius=T.RADIUS_SM,
        fg_color=T.SURFACE_ALT, button_color=T.SURFACE_HOVER, button_hover_color=T.BORDER,
        text_color=T.TEXT, dropdown_fg_color=T.SURFACE, dropdown_hover_color=T.SURFACE_ALT,
        dropdown_text_color=T.TEXT, font=T.font(13), dropdown_font=T.font(13), **kw,
    )


def switch(master, text, variable=None, command=None, **kw) -> ctk.CTkSwitch:
    return ctk.CTkSwitch(
        master, text=text, variable=variable, command=command, font=T.font(13), text_color=T.TEXT,
        progress_color=T.ACCENT, fg_color=T.BORDER, button_color=("#FFFFFF", "#E7EAF0"),
        button_hover_color=("#F3F5F9", "#FFFFFF"), switch_width=38, switch_height=20, **kw,
    )


def segmented(master, values, command=None, **kw) -> ctk.CTkSegmentedButton:
    return ctk.CTkSegmentedButton(
        master, values=values, command=command, font=T.font(13), height=36, corner_radius=T.RADIUS_SM,
        fg_color=T.SURFACE_ALT, selected_color=("#D9CEFF", "#4631A8"), selected_hover_color=("#CDBFFF", "#523AC0"),
        unselected_color=T.SURFACE_ALT, unselected_hover_color=T.SURFACE_HOVER,
        text_color=T.TEXT_STRONG, **kw,
    )


def textbox(master, **kw) -> ctk.CTkTextbox:
    kw.setdefault("font", T.font(13))
    return ctk.CTkTextbox(
        master, corner_radius=T.RADIUS_SM, fg_color=T.SURFACE_ALT, border_color=T.BORDER, border_width=1,
        text_color=T.TEXT, scrollbar_button_color=T.BORDER, scrollbar_button_hover_color=T.FAINT, **kw,
    )


def scrollbar(master, command, orientation="vertical") -> ctk.CTkScrollbar:
    return ctk.CTkScrollbar(master, command=command, orientation=orientation,
                            button_color=T.BORDER, button_hover_color=T.FAINT, fg_color="transparent")


class Badge(ctk.CTkLabel):
    def __init__(self, master, text="", tone="neutral", **kw):
        fg, bg = TONES[tone]
        super().__init__(master, text=text, font=T.font(11, "semi"), text_color=fg, fg_color=bg,
                         corner_radius=6, padx=8, pady=1, **kw)

    def set(self, text, tone="neutral"):
        fg, bg = TONES[tone]
        self.configure(text=text, text_color=fg, fg_color=bg)


class StatTile(Card):
    """Big number with a caption, e.g. '128' / 'Files'."""

    def __init__(self, master, caption: str, value: str = "-", tone="neutral"):
        super().__init__(master)
        self.caption = caption
        inner = transparent(self)
        inner.pack(fill="both", expand=True, padx=16, pady=12)
        self.value_lbl = label(inner, value, 22, T.TEXT_STRONG, "semi", anchor="w")
        self.value_lbl.pack(anchor="w")
        label(inner, caption, 12, T.MUTED, anchor="w").pack(anchor="w")
        self.set(value, tone)

    def set(self, value, tone="neutral"):
        color = T.TEXT_STRONG if tone == "neutral" else TONES[tone][0]
        self.value_lbl.configure(text=str(value), text_color=color)


def section_title(master, title: str, hint: str = "") -> ctk.CTkFrame:
    box = transparent(master)
    label(box, title, 15, T.TEXT_STRONG, "semi", anchor="w").pack(anchor="w")
    if hint:
        label(box, hint, 12, T.MUTED, anchor="w", justify="left").pack(anchor="w", pady=(2, 0))
    return box


def divider(master) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, height=1, fg_color=T.BORDER, corner_radius=0)


# ------------------------------------------------------------------ data table
_SIZE_RE = re.compile(r"^([\d.,]+)\s*(B|KB|MB|GB)$")
_SIZE_MULT = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


def _sort_key(text: str):
    text = str(text)
    m = _SIZE_RE.match(text)
    if m:
        return (0, float(m.group(1).replace(",", "")) * _SIZE_MULT[m.group(2)], "")
    parts = [(int(tok) if tok.isdigit() else tok.lower()) for tok in re.split(r"(\d+)", text) if tok != ""]
    # keep int/str comparable by tagging each chunk
    return (1, 0, [(0, p) if isinstance(p, int) else (1, p) for p in parts])


class DataTable(ctk.CTkFrame):
    """ttk.Treeview with themed scrollbars, zebra rows, tone tags and sortable headings."""

    def __init__(self, master, columns: Sequence[Dict], sortable=True, selectmode="browse",
                 on_select: Optional[Callable] = None, on_double_click: Optional[Callable] = None,
                 on_click: Optional[Callable] = None, horizontal_scroll=False):
        super().__init__(master, fg_color="transparent")
        self.columns = list(columns)
        self.sortable = sortable
        self._sort_state = (None, False)
        self._count = 0
        self._tone_tags: Dict[str, tuple] = {}

        ids = [c["id"] for c in self.columns]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", style="Slack.Treeview",
                                 selectmode=selectmode, height=6)
        for c in self.columns:
            self.tree.heading(c["id"], text=c["title"], anchor=c.get("anchor", "w"),
                              command=(lambda cid=c["id"]: self.sort_by(cid)) if sortable and c.get("sort", True) else "")
            self.tree.column(c["id"], width=c.get("width", 120), minwidth=c.get("minwidth", 40),
                             anchor=c.get("anchor", "w"), stretch=c.get("stretch", False))

        self.vsb = scrollbar(self, self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)
        if horizontal_scroll:
            self.hsb = scrollbar(self, self.tree.xview, "horizontal")
            self.tree.configure(xscrollcommand=self.hsb.set)
            self.hsb.pack(side="bottom", fill="x")
        self.vsb.pack(side="right", fill="y", padx=(2, 2), pady=2)
        self.tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)

        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: on_select())
        if on_double_click:
            self.tree.bind("<Double-1>", on_double_click)
        if on_click:
            self.tree.bind("<Button-1>", on_click)

        T.register_table(self)
        self.restyle()

    # tones ---------------------------------------------------------------
    def tone_tag(self, name: str, color):
        self._tone_tags[name] = color
        self.tree.tag_configure(name, foreground=T.resolve(color))

    def restyle(self):
        self.tree.tag_configure("even", background=T.resolve(T.SURFACE))
        self.tree.tag_configure("odd", background=T.resolve(ZEBRA))
        for name, color in self._tone_tags.items():
            self.tree.tag_configure(name, foreground=T.resolve(color))

    # data ----------------------------------------------------------------
    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._count = 0

    def insert(self, values, tags=(), iid=None):
        stripe = "odd" if self._count % 2 else "even"
        self._count += 1
        return self.tree.insert("", "end", iid=iid, values=values, tags=(*tags, stripe))

    def set_cell(self, iid, column, value):
        self.tree.set(iid, column, value)

    def selection(self) -> List[str]:
        return list(self.tree.selection())

    def row_values(self, iid):
        return self.tree.item(iid, "values")

    def _restripe(self):
        for i, iid in enumerate(self.tree.get_children()):
            tags = [t for t in self.tree.item(iid, "tags") if t not in ("odd", "even")]
            self.tree.item(iid, tags=(*tags, "odd" if i % 2 else "even"))

    def sort_by(self, col_id, reverse=None):
        prev_col, prev_rev = self._sort_state
        if reverse is None:
            reverse = (not prev_rev) if prev_col == col_id else False
        rows = [(_sort_key(self.tree.set(iid, col_id)), iid) for iid in self.tree.get_children()]
        rows.sort(key=lambda r: r[0], reverse=reverse)
        for index, (_k, iid) in enumerate(rows):
            self.tree.move(iid, "", index)
        self._restripe()
        self._sort_state = (col_id, reverse)
        for c in self.columns:
            arrow = (" â–¼" if reverse else " â–²") if c["id"] == col_id else ""
            self.tree.heading(c["id"], text=c["title"] + arrow)


# ------------------------------------------------------------------- toast
class ToastHost:
    """One transient notification at a time, bottom-right of `parent`."""

    KIND = {
        "success": ("success", "success"),
        "info": ("info", "info"),
        "warning": ("warning", "warning"),
        "error": ("error", "danger"),
    }

    def __init__(self, parent, bottom_offset=16):
        self.parent = parent
        self.bottom_offset = bottom_offset
        self._frame: Optional[ctk.CTkFrame] = None
        self._timer = None

    def show(self, text: str, kind: str = "success", ms: int = 3600):
        self.hide()
        icon_name, tone = self.KIND.get(kind, self.KIND["info"])
        fg, soft = TONES[tone]
        frame = ctk.CTkFrame(self.parent, fg_color=T.SURFACE, border_color=fg, border_width=1, corner_radius=T.RADIUS)
        badge = ctk.CTkLabel(frame, text=T.ICONS[icon_name], font=T.icon_font(15), text_color=fg,
                             fg_color=soft, width=30, height=30, corner_radius=8)
        badge.pack(side="left", padx=(10, 8), pady=10)
        label(frame, text, 13, T.TEXT, wraplength=420, justify="left").pack(side="left", padx=(0, 10), pady=10)
        ctk.CTkButton(frame, text=T.ICONS["close"], width=26, height=26, font=T.icon_font(11),
                      fg_color="transparent", hover_color=T.SURFACE_ALT, text_color=T.MUTED,
                      command=self.hide).pack(side="left", padx=(0, 8))
        frame.place(relx=1.0, rely=1.0, x=-20, y=-self.bottom_offset, anchor="se")
        frame.lift()
        self._frame = frame
        self._timer = self.parent.after(ms, self.hide)

    def hide(self):
        if self._timer is not None:
            try:
                self.parent.after_cancel(self._timer)
            except Exception:
                pass
            self._timer = None
        if self._frame is not None:
            try:
                self._frame.destroy()
            except Exception:
                pass
            self._frame = None


# ----------------------------------------------------------------- nav item
class NavItem(ctk.CTkFrame):
    def __init__(self, master, icon_name: str, text: str, hint: str = "", command=None):
        super().__init__(master, fg_color="transparent", corner_radius=T.RADIUS_SM, height=40)
        self.command = command
        self.active = False
        self.pack_propagate(False)

        self.bar = ctk.CTkFrame(self, width=3, height=18, fg_color="transparent", corner_radius=2)
        self.bar.pack(side="left", padx=(4, 8))
        self.icon_lbl = ctk.CTkLabel(self, text=T.ICONS[icon_name], font=T.icon_font(16),
                                     text_color=T.MUTED, width=22)
        self.icon_lbl.pack(side="left")
        self.text_lbl = ctk.CTkLabel(self, text=text, font=T.font(13), text_color=T.TEXT, anchor="w")
        self.text_lbl.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self.hint_lbl = ctk.CTkLabel(self, text=hint, font=T.font(10), text_color=T.FAINT)
        self.hint_lbl.pack(side="right", padx=(0, 10))

        for w in (self, self.bar, self.icon_lbl, self.text_lbl, self.hint_lbl):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.configure(cursor="hand2")

    def _click(self, _e=None):
        if self.command:
            self.command()

    def _enter(self, _e=None):
        if not self.active:
            self.configure(fg_color=T.SURFACE_ALT)

    def _leave(self, _e=None):
        if not self.active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool):
        self.active = active
        if active:
            self.configure(fg_color=T.ACCENT_SOFT)
            self.bar.configure(fg_color=T.ACCENT)
            self.icon_lbl.configure(text_color=T.ACCENT)
            self.text_lbl.configure(text_color=T.TEXT_STRONG, font=T.font(13, "semi"))
        else:
            self.configure(fg_color="transparent")
            self.bar.configure(fg_color="transparent")
            self.icon_lbl.configure(text_color=T.MUTED)
            self.text_lbl.configure(text_color=T.TEXT, font=T.font(13))


class EmptyState(ctk.CTkFrame):
    def __init__(self, master, icon_name: str, title: str, text: str):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=T.ICONS[icon_name], font=T.icon_font(34), text_color=T.FAINT).pack(pady=(0, 8))
        label(self, title, 15, T.TEXT, "semi").pack()
        label(self, text, 12, T.MUTED, justify="center", wraplength=380).pack(pady=(4, 0))

