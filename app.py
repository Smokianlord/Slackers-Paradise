"""Slackers-Paradise - folder & file automation for Windows."""
import os


def _enable_high_dpi():
    """Must run before Tk is created so text and icons stay sharp on 1440p / 4K displays."""
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    _enable_high_dpi()
    from ui.shell import SlackersParadiseApp
    SlackersParadiseApp().mainloop()


if __name__ == "__main__":
    main()
