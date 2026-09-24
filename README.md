# Slackers-Paradise Pro

<p align="center">
  <img width="850" alt="Slackers-Paradise Preview" src="https://github.com/user-attachments/assets/4b603c7c-59fa-49af-840f-e9e724d192c9" />
</p>

<p align="center">
  <a href="https://github.com/Smokianlord/Slackers-Paradise/releases"><img src="https://img.shields.io/badge/release-v3.0.0-blue.svg?style=for-the-badge" alt="Release" /></a>
  <img src="https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4.svg?style=for-the-badge&logo=windows" alt="Windows" />
  <img src="https://img.shields.io/badge/python-3.12-3776ab.svg?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge" alt="License" />
</p>

---

## 🚀 About Slackers-Paradise

**Slackers-Paradise** is an all-in-one productivity and utility suite for Windows. Originally born from standalone `.bat` automation scripts, **v3.0.0** completely transforms the project into a professional desktop application with a top toolbar ribbon, modern CustomTkinter interface, High-DPI scaling, and powerful file automation tools.

Whether you are scaffolding project directory structures, cataloging folders into Markdown/CSV/Trees, batch renaming thousands of files with zero collisions and full 1-click Undo, running game shortcuts with staggered execution, or sweeping junk files, **Slackers-Paradise** makes Windows productivity effortless.

---

## ✨ Features at a Glance

| Tool | Icon | Description | Key Capabilities |
|---|:---:|---|---|
| **Build-a-Folder Pro** | 📁 | Advanced Directory Scaffolder | Nested subfolders (`src/components/ui`), Sequence Generator (`Episode_{01..12}`), 1-click Presets (Web, Python, Media, School), Windows reserved name checks (`CON`, `PRN`). |
| **FolderFolio Pro** | 📋 | Directory Tree & Metadata Cataloger | Export to **TXT List**, **ASCII Tree**, **CSV Table**, **Markdown Table**, or **JSON**. Filter by extension, include/exclude hidden files, 1-click **Copy to Clipboard**. |
| **RenameRoulette Pro** | 🎲 | Safe Multi-Mode Batch Renamer | **Roulette** (4-digit, 6-digit, 8-digit, Hex, UUID), **Sequential Numbering** (`Item_001.ext`), **Find & Replace**, **Date Stamp**, **Case Transform**. Two-phase atomic renaming + **1-Click Undo**. |
| **ShortcutExecutor Pro** | ⚡ | Staggered App & Shortcut Runner | Scans `.lnk`, `.url`, `.bat`, `.cmd`, `.exe`. **Staggered execution delay** (250ms - 2000ms) prevents PC freeze. Resolves `.lnk` targets, filter search, and **Abort** button. |
| **SlackerCleaner Pro** | 🧹 | Instant Cache & Junk Sweeper | 1-click scan and clean for Windows User Temp (`%TEMP%`), System Temp, Empty Folders, and Broken `.lnk` shortcuts. Skips in-use files safely. |

---

## 🖥 Top Toolbar & Modern UI

- **Top Action Ribbon**: Modeled after modern professional apps with branding, version badge, direct tool navigation buttons, and instant utilities (**Explorer**, **PowerShell Terminal**, **Theme Switcher**, **Settings**, and **Help**).
- **Unified Workspace & Detachable Windows**: Work inside a clean, single-window tabbed interface, or click **"↗ Detach Window"** to pop any tool into its own floating window for dual-monitor setups.
- **Active Directory Navigator**: Global breadcrumb bar with path entry, file dialog browser, path clipboard copy, and recent folder history dropdown.
- **Live Status & Activity Drawer**: Bottom bar showing real-time drive free space (`💽 C: 334 GB Free`), operation status indicators, and a collapsible Activity Console (`Ctrl+L`) with logs, copy, and clear buttons.
- **Per-Monitor High-DPI Awareness**: Crystal-clear typography and icons on 1080p, 1440p, and 4K displays.

---

## ⌨ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| <kbd>Ctrl</kbd> + <kbd>1</kbd> | Switch to **Build-a-Folder Pro** |
| <kbd>Ctrl</kbd> + <kbd>2</kbd> | Switch to **FolderFolio Pro** |
| <kbd>Ctrl</kbd> + <kbd>3</kbd> | Switch to **RenameRoulette Pro** |
| <kbd>Ctrl</kbd> + <kbd>4</kbd> | Switch to **ShortcutExecutor Pro** |
| <kbd>Ctrl</kbd> + <kbd>5</kbd> | Switch to **SlackerCleaner Pro** |
| <kbd>Ctrl</kbd> + <kbd>O</kbd> | Browse active directory |
| <kbd>Ctrl</kbd> + <kbd>L</kbd> | Toggle live activity console drawer |
| <kbd>F1</kbd> | Open Help & Shortcut Guide |

---

## 📦 Installation & Getting Started

### Method 1: Portable Executable (Recommended)
No Python installation required:
1. Download `Slackers-Paradise-Windows-x64.zip` or `Slackers-Paradise.exe` from the latest [GitHub Releases](https://github.com/Smokianlord/Slackers-Paradise/releases).
2. Extract the archive or launch `Slackers-Paradise.exe` directly.

### Method 2: Run from Python Source
Requirements: Python 3.10+ (Python 3.12 recommended).

```powershell
# Clone the repository
git clone https://github.com/Smokianlord/Slackers-Paradise.git
cd Slackers-Paradise

# Install dependencies
pip install -r requirements.txt

# Launch application
python app.py
```

### Method 3: Build Standalone Executable with PyInstaller
```powershell
python -m PyInstaller Slackers-Paradise.spec --noconfirm
```
The compiled executable will be located in `dist/Slackers-Paradise.exe`.

---

## 🛡 Safety & Reliability Safeguards

- **Atomic Two-Phase Renaming**: All batch renames use temporary GUID intermediate files to eliminate chain overwrites and filename collisions.
- **Full Undo Stack**: Accidental renames can be restored back to original filenames with 1 click.
- **System Freeze Prevention**: Launching multiple shortcuts uses staggered time delays with an instant `Abort` button.
- **Windows Path Validation**: Prevents crashes from reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, etc.) and automatically sanitizes illegal characters.
- **Safe Junk Sweeper**: Locked or in-use files during cache cleaning are gracefully bypassed without application errors.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
