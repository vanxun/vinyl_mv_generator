@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 音频可视化生成器
set "PYTHON="

if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\Anaconda3\python.exe" set "PYTHON=%USERPROFILE%\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\miniconda3\python.exe" set "PYTHON=%USERPROFILE%\miniconda3\python.exe"

if not defined PYTHON (
  where python.exe >nul 2>nul
  if not errorlevel 1 set "PYTHON=python.exe"
)

if not defined PYTHON (
  echo [ERROR] Python not found.
  pause
  exit /b 1
)

"%PYTHON%" "%~dp0vinyl_mv_generator.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Program exited with an error.
  pause
)
