@echo off
setlocal

:: Prompt the user for the folder path
set /p folder="Enter the folder path containing shortcuts: "

:: Check if the folder exists
if not exist "%folder%" (
    echo The specified folder does not exist.
    exit /b
)

echo Running all shortcuts in "%folder%"...

for %%f in ("%folder%\*.lnk") do (
    echo Running shortcut: "%%f"
    start "" "%%f"
)

echo All shortcuts have been executed.
pause
