@echo off
title Market Dashboard
echo ================================================
echo        MARKET DASHBOARD - AUTO START
echo ================================================
echo.

REM Check if Python 3.11 is available
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 nahi mila!
    echo.
    echo Please install Python 3.11 from:
    echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
    echo Install karte waqt "Add Python to PATH" tick karna mat bhoolo!
    pause
    exit
)

echo [1/3] Python 3.11 mil gaya!
echo.
echo [2/3] Required packages install ho rahe hain...
py -3.11 -m pip install streamlit yfinance plotly pandas pytz requests chardet --quiet --upgrade
echo      Done!
echo.
echo [3/3] App start ho rahi hai...
echo       Browser mein automatically open hoga.
echo       Band karne ke liye: Ctrl+C dabao
echo ================================================
echo.
cd /d "%~dp0"
py -3.11 -m streamlit run main.py
pause
