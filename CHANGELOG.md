# Changelog

All notable changes to **Slackers-Paradise** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] - 2026-09-25 (Complete Modern Overhaul)

### 🌟 Major Highlights & Modern UI Overhaul
- **Top Application Toolbar**: Introduced a modern desktop top ribbon toolbar with brand icon, version badge, direct tool navigation buttons (`Build Folders`, `Folder Folio`, `Rename Roulette`, `Shortcut Runner`, `Slacker Cleaner`), and quick system action buttons (`Explorer`, `PowerShell Terminal`, `Theme Toggle`, `Settings`, `Help`).
- **Unified Clean Workspace**: Replaced cluttered floating multi-window popups with a modern, high-contrast tabbed workspace. Includes an instant "↗ Detach Window" button for dual-monitor or multi-window multitasking.
- **Active Directory Breadcrumb Bar**: Quick path navigator with real-time text input, directory browser, path copy, and recent folder history dropdown.
- **Live Status & Activity Drawer**: Bottom status bar displaying live drive free space (`💽 C: 334 GB Free`), operation status indicators, and an expandable collapsible Activity Console (`Ctrl+L`) with logs, copy, and clear buttons.
- **Windows High-DPI Awareness**: Integrated native Windows DPI scaling (`shcore.SetProcessDpiAwareness`) for crisp text, sharp icons, and zero blurriness on 1080p, 1440p, and 4K monitors.
- **Keyboard Shortcuts**: Added full keyboard navigation (`Ctrl+1..5`, `Ctrl+O`, `Ctrl+L`, `F1`).

### 🚀 Better Relevant Features
- **Build-a-Folder Pro**:
  - **Nested Subfolder Creation**: Full support for hierarchical paths (e.g. `src/components/ui`, `assets/images/icons`) with parent directory auto-creation.
  - **Sequence / Range Expander**: Added sequence syntax (e.g. `Episode_{01..12}`, `Chapter_{1..5}`, `Cam_{A..D}`) with automatic range expansion.
  - **Project Presets & Templates**: 1-click generation for Web Projects, Python Apps, Media Creator directories, University/School setups, and 12-Month organizers.
  - **Windows Reserved Name Sanitization**: Validates and protects against illegal characters (`<>:"|?*`) and reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- **FolderFolio Pro**:
  - **Multi-Format Exports**: Export directory trees to **Plain Text (`.txt`)**, **ASCII Tree (`Tree.txt`)**, **CSV with Metadata (`.csv`)**, **Markdown (`.md`)**, or **JSON (`.json`)**.
  - **Metadata & Filters**: Recursive or shallow scans with file sizes, modification timestamps, extension breakdown, and pattern filters.
  - **1-Click Clipboard Sharing**: One-click button to copy catalog directly to clipboard for Discord, GitHub, or Notion.
- **RenameRoulette Pro**:
  - **Multiple Renaming Engines**: Added Sequential Numbering (`Item_001.ext`), Find & Replace, Date & Timestamping (`YYYY-MM-DD`), Case Transformers (lower, UPPER, Title, kebab-case, snake_case), alongside Random Roulette (4-digit, 6-digit, 8-digit, hex, alphanumeric, UUID).
  - **Two-Phase Safe Atomic Renaming**: Uses intermediate temporary GUID names during batch renames to prevent file overwrites and chain collisions.
  - **1-Click Undo History**: Fully reversible renames—click "↺ Undo Last Rename" to instantly restore original filenames.
- **ShortcutExecutor Pro**:
  - **Staggered Launch Engine**: Configurable execution delays (0ms, 250ms, 500ms, 1000ms, 2000ms) with a live progress bar and an instant **Abort** button to prevent system freezing when opening dozens of shortcuts.
  - **Multi-Type Support**: Discovers and runs `.lnk`, `.url`, `.bat`, `.cmd`, and `.exe` files.
  - **Target Resolution**: Reads `.lnk` target paths and validates whether destination files still exist.
  - **Checklist & Quick Search**: Checkbox selection with "Select All", "Deselect All", and real-time search filtering.
- **NEW TOOL: SlackerCleaner Pro**:
  - Designed for slackers who want their PC clutter-free with one click:
    - User Temp (`%TEMP%`) and Windows Temp sweeper.
    - Empty directory detection and removal.
    - Broken shortcut finder (`.lnk` pointing to deleted/missing files).
    - Safe execution that skips locked/in-use files gracefully.

### 🐛 Bug Fixes & Optimizations
- Fixed blurry UI scaling on Windows high-DPI displays.
- Fixed mousewheel scrolling collision bug caused by global `bind_all` in secondary windows.
- Fixed directory creation crash when typing forward or backward slashes in subfolder paths.
- Fixed crashes on Windows reserved file/folder names.
- Fixed system freeze when launching multiple shortcuts concurrently.
- Fixed filename collisions during batch rename operations.
- Fixed missing `D:\Gaming Shortcuts` fallback when drive D: is not mounted.

---

## [2.0.0] - 2026-09-24
- Converted original BAT scripts into a Python Tkinter launcher.
- Split features into separate pop-up windows.
- Added basic folder validation and safety confirmation dialogs.

---

## [1.0.0] - 2026-09-23
- Initial batch script collection (`Build-a-Folder.bat`, `FolderFolio.bat`, `RenameRoulette.bat`, `ShortcutExecutor.bat`).
