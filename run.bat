@echo off
title Hand Gesture Windows Controller
echo =======================================================
echo   Hand Gesture Windows Controller (Windows 11)
echo   Initializing environment and starting camera stream...
echo =======================================================

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe main.py %*
) else (
    echo [ERROR] Virtual environment not found. Please run:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
)
