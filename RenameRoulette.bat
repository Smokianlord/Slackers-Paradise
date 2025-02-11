@echo off
setlocal enabledelayedexpansion

:: Prompt for folder path
set /p "folder=Enter the folder path: "

:: Check if the folder exists
if not exist "!folder!" (
    echo The specified folder does not exist.
    exit /b
)

:: Change to the specified folder
cd /d "!folder!"

:: Initialize a counter
set count=0

:: Loop through each file in the folder
for %%F in (*) do (
    set /a "randomNum=!random! %% 9000 + 1000"
    ren "%%F" "!randomNum!%%~xF"
    set /a count+=1
)

echo Renamed !count! files.
pause
