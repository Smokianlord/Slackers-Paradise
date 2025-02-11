@echo off
setlocal

:: Prompt the user for the folder path
set /p folderPath="Enter the folder path: "

:: Check if the folder exists
if not exist "%folderPath%" (
    echo The specified folder does not exist.
    exit /b
)

:: Define the output text file
set outputFile="List.txt"

:: List all files and folders in the specified folder and save to the text file
dir "%folderPath%" /b > %outputFile%

:: Notify the user
echo All files and folders in %folderPath% have been listed in %outputFile%.

endlocal
pause
