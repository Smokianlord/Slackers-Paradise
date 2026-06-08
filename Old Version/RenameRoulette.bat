::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFChcQxOQPX36PLQR6ebHy+WQrEESVeYsRJ3e1LWDJa4a6UqE
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdCuDJH6N4GolKidnQAWBN26oFfgs6fr66+OUp3EvUew+dYrp1aGCJfQH7wvhbZNN
::YB416Ek+ZG8=
::
::
::978f952a14a936cc963da21a135fa983
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
