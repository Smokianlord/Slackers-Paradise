@echo off
set "folder=D:\Gaming Shortcuts"

echo Running all shortcuts in "%folder%"...

for %%f in ("%folder%\*.lnk") do (
    echo Running shortcut: "%%f"
    start "" "%%f"
)

echo All shortcuts have been executed.
pause
