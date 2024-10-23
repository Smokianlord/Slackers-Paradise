@echo off
setlocal enabledelayedexpansion

:loop
REM Prompt the user for a folder name
set /p folderName="Enter a folder name (type 'done' to finish): "

REM Check if the user typed "done"
if /i "!folderName!"=="done" (
    echo Finished creating folders.
    goto end
)

REM Create the folder
mkdir "!folderName!"

echo Folder "!folderName!" created successfully.
goto loop

:end
pause
