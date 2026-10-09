"""Design tokens for Slackers-Paradise: colors, fonts, icons and ttk styling.

Colors are (light, dark) tuples understood by customtkinter. Anything that has to
be a plain string (ttk / tk widgets) goes through `resolve()`.
"""
import weakref
from tkinter import ttk

import customtkinter as ctk

# ----------------------------------------------------------------------------
# Palette                      light        dark
# ----------------------------------------------------------------------------
BG = ("#F4F2FC", "#0B0A15")
SIDEBAR = ("#FFFFFF", "#0F0E1D")
SURFACE = ("#FFFFFF", "#15142A")
SURFACE_ALT = ("#EFECFA", "#1C1B38")
SURFACE_HOVER = ("#E4DFF6", "#272547")
BORDER = ("#DDD8F0", "#2A2850")
TEXT = ("#17142E", "#E9E7FB")
TEXT_STRONG = ("#0E0B24", "#FFFFFF")
MUTED = ("#6B6790", "#9693C2")
FAINT = ("#A09CC0", "#605D8F")

ACCENT = ("#6D4AFF", "#8265FF")
ACCENT_HOVER = ("#5A38EA", "#6F4FF0")
ACCENT_SOFT = ("#ECE6FF", "#2A2060")
ON_ACCENT = ("#FFFFFF", "#FFFFFF")

SUCCESS = ("#0F8F6B", "#34E3B0")
SUCCESS_SOFT = ("#D5F7EA", "#0F3B33")
WARNING = ("#B45309", "#FFC857")
WARNING_SOFT = ("#FFF0CC", "#3D3010")
DANGER = ("#D6285B", "#FF6B93")
DANGER_HOVER = ("#B01E48", "#F2507C")
DANGER_FILL = ("#D6285B", "#E0386B")
DANGER_FILL_HOVER = ("#B01E48", "#C42A58")
DANGER_SOFT = ("#FFE0E9", "#401428")
INFO = ("#0A7FB5", "#4CC9F0")
INFO_SOFT = ("#DDF3FC", "#10304A")

RADIUS = 10
RADIUS_SM = 8

FONT_UI = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"
FONT_MONO = "Cascadia Mono"      # falls back to Consolas via _mono_family()
FONT_ICON = "Segoe MDL2 Assets"

# Segoe MDL2 Assets glyphs
ICONS = {
    "build": "",
    "folio": "",
    "rename": "",
    "shortcuts": "",
    "cleaner": "",
    "settings": "",
    "help": "",
    "theme": "",
    "search": "",
    "refresh": "",
    "copy": "",
    "save": "",
    "folder": "",
    "terminal": "",
    "check": "",
    "warning": "",
    "info": "",
    "error": "",
    "success": "",
    "bolt": "",
    "wrench": "",
    "undo": "",
    "add": "",
    "delete": "",
    "close": "",
    "popout": "",
    "log": "",
    "chevron_down": "",
    "chevron_up": "",
    "history": "",
    "drive": "",
}

_appearance_state = {"mode": "Dark"}
_tables = weakref.WeakSet()
_font_cache = {}
_mono_cache = {}


def set_mode(mode: str):
    _appearance_state["mode"] = mode


def is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def resolve(color) -> str:
    """Pick the concrete color string for the current appearance."""
    if isinstance(color, (tuple, list)):
        return color[1] if is_dark() else color[0]
    return color


def font(size: int = 13, weight: str = "normal", family: str = None) -> ctk.CTkFont:
    """Cached CTkFont. weight: 'normal' | 'bold' | 'semi'."""
    key = (size, weight, family)
    if key not in _font_cache:
        if weight == "semi":
            _font_cache[key] = ctk.CTkFont(family=family or FONT_SEMI, size=size)
        else:
            _font_cache[key] = ctk.CTkFont(family=family or FONT_UI, size=size, weight=weight)
    return _font_cache[key]


def mono(size: int = 12) -> ctk.CTkFont:
    return font(size, "normal", family=_mono_family())


def _mono_family() -> str:
    if "family" not in _mono_cache:
        import tkinter.font as tkfont
        families = set(tkfont.families())
        _mono_cache["family"] = FONT_MONO if FONT_MONO in families else "Consolas"
    return _mono_cache["family"]


def icon_font(size: int = 16) -> ctk.CTkFont:
    return font(size, "normal", family=FONT_ICON)


# ----------------------------------------------------------------------------
# ttk (Treeview) styling
# ----------------------------------------------------------------------------
def register_table(table):
    _tables.add(table)


def apply_ttk_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
    bg = resolve(SURFACE)
    alt = resolve(SURFACE_ALT)
    fg = resolve(TEXT)
    head_fg = resolve(MUTED)

    style.layout("Slack.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(
        "Slack.Treeview",
        background=bg, fieldbackground=bg, foreground=fg,
        borderwidth=0, relief="flat", rowheight=int(34 * scale),
        font=(FONT_UI, 10),
    )
    style.map(
        "Slack.Treeview",
        background=[("selected", resolve(ACCENT_SOFT))],
        foreground=[("selected", resolve(TEXT_STRONG))],
    )
    style.configure(
        "Slack.Treeview.Heading",
        background=alt, foreground=head_fg, relief="flat", borderwidth=0,
        padding=(10, int(7 * scale)), font=(FONT_SEMI, 9),
    )
    style.map("Slack.Treeview.Heading", background=[("active", resolve(SURFACE_HOVER))])

    for table in list(_tables):
        try:
            table.restyle()
        except Exception:
            pass
