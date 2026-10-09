# Slackers-Paradise v4.0.0

A ground-up redesign focused on polish, safety and correctness.

## Highlights
- **New interface**: sidebar navigation, violet design system with dark and light themes, raised 3D-style buttons, non-blocking toast notifications, crisp vector icons and sortable data tables.
- **Build-a-Folder rewritten**: one folder per line - commas are no longer separators, so titles like *"Battle Through the Heaven: Choose Three Out of Five Cheats, a Perfect Start!"* stay intact.
- **Preview + fix suggestions**: every line is checked live; invalid ones show why and a suggested name (`:` becomes ` - `, `?` removed, reserved names, trailing dots...). Fix one line, fix all, or apply at creation.
- **Undo for folder creation**, saved templates, `.txt` import.

## Improvements
- RenameRoulette: natural sorting, regex / match-case replace, file-type filter in every mode, invalid-name detection, safe multi-level undo (swaps now restore correctly).
- FolderFolio: background scanning, live filter, tree export now honours filters, Excel-friendly CSV.
- ShortcutExecutor: thread-safe launching, instant Stop, per-row launch, no hard-coded personal paths.
- SlackerCleaner: nested empty folders, temp-age threshold, Recycle Bin for folders/shortcuts, protection for system and profile folders.
- Settings are validated, saved atomically, and window size / last folder are remembered.
- Automated test suite (`python -m unittest discover -s tests -t .`).
