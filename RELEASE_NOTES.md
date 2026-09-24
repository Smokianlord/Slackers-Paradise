# Slackers-Paradise Pro v3.0.0 Release Notes

**Slackers-Paradise Pro v3.0.0** is a complete, ground-up overhaul of the utility suite. It delivers a modern, high-contrast desktop UI with a professional top ribbon toolbar, high-DPI scaling, native Windows optimizations, new productivity tools, and full crash & collision safeguards.

---

### 🌟 What's New in v3.0.0

#### 1. Modern Desktop Top Toolbar & Unified Workspace
- **Top Application Ribbon**: Sleek toolbar with app branding, version badge, direct tool navigation buttons, and system utilities (**Explorer**, **PowerShell Terminal**, **Dark/Light Theme Toggle**, **Settings**, and **Help**).
- **Unified Clean Workspace**: Replaced chaotic floating popup windows with a unified tabbed view, while preserving a **"↗ Detach Window"** button for dual-monitor or multi-window setups.
- **Context Directory Bar**: Active working directory navigator with real-time text input, directory browser, path copy, and recent folder history dropdown.
- **Status & Activity Console**: Bottom status bar displaying live drive free space (`💽 C: 334 GB Free`), real-time operation status indicators, and an expandable collapsible Activity Console (`Ctrl+L`) with logs, copy, and clear.
- **Windows High-DPI Scaling**: Full per-monitor DPI awareness (`shcore.SetProcessDpiAwareness`) for crisp text and sharp icons on 1080p, 1440p, and 4K displays.
- **Keyboard Shortcuts**: Quick hotkeys (`Ctrl+1..5` for tools, `Ctrl+O` for folder browse, `Ctrl+L` for activity log, `F1` for help).

#### 2. Enhanced Productivity Tools
- **📁 Build-a-Folder Pro**:
  - Full support for nested subfolder paths (e.g. `src/components/ui`, `assets/images/icons`).
  - Sequence generator: Expands patterns like `Episode_{01..12}`, `Chapter_{1..5}`, or `Cam_{A..D}` automatically.
  - 1-click project templates (Web, Python, Media Creator, School/University, 12 Months).
  - Reserved Windows names validation (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- **📋 FolderFolio Pro**:
  - Export directory trees to **Plain Text (`.txt`)**, **ASCII Tree (`Tree.txt`)**, **CSV with Metadata (`.csv`)**, **Markdown Table (`.md`)**, or **JSON (`.json`)**.
  - Recursive or shallow folder scans with file sizes, modification timestamps, and pattern filters.
  - 1-click clipboard sharing for Discord, GitHub, and Notion.
- **🎲 RenameRoulette Pro**:
  - Multiple renaming modes: Random roulette (4-digit, 6-digit, 8-digit, hex, alphanumeric, UUID), Sequential numbering (`Item_001.ext`), Find & Replace, Date & Timestamping (`YYYY-MM-DD`), and Case Transformers.
  - **Two-phase safe atomic renaming**: Uses temporary GUID intermediate filenames to avoid chain collisions and file overwrites.
  - **1-Click Undo**: Reversible renames—click "↺ Undo Last Rename" to instantly restore original filenames.
- **⚡ ShortcutExecutor Pro**:
  - **Staggered launch engine**: Configurable delay (0ms, 250ms, 500ms, 1000ms, 2000ms) with a live progress bar and an instant **Abort** button to prevent CPU/RAM freezing.
  - Multi-type support: Discovers and executes `.lnk`, `.url`, `.bat`, `.cmd`, and `.exe` files.
  - Target path inspection: Resolves `.lnk` targets and identifies broken/missing destinations.
  - Checkbox selection with "Select All", "Deselect All", and real-time search filtering.
- **🧹 NEW: SlackerCleaner Pro**:
  - Safely sweeps Windows User Temp (`%TEMP%`), empty folders in any directory, and broken shortcuts.
  - Confirmation dialog with reclaimed space calculation, gracefully skipping locked/in-use files.

---

### 🐛 Bug Fixes
- Fixed text and icon blurriness on Windows high-DPI displays.
- Fixed mousewheel scrolling collisions caused by global `bind_all` in pop-up windows.
- Fixed directory creation crash when typing `/` or `\` in subfolder paths.
- Fixed crashes on Windows reserved file/folder names.
- Fixed system freeze when launching dozens of shortcuts simultaneously.
- Fixed file collisions and potential data loss during batch rename operations.
- Fixed missing `D:\Gaming Shortcuts` drive crash with graceful fallback to Desktop.

---

### 📦 Assets Included
- `Slackers-Paradise.exe`: Standalone portable Windows executable (no Python installation required).
- `Slackers-Paradise-Windows-x64.zip`: Complete release bundle including executable, README, and CHANGELOG.
