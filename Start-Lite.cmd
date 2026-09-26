@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONNOUSERSITE=1
set PYTHONHOME=
set PYTHONPATH=
if exist ".buildenv\Scripts\python.exe" (
  ".buildenv\Scripts\python.exe" server.py
) else if exist "runtime\python\python.exe" (
  "runtime\python\python.exe" server.py
) else (
  "..\.agents\skills\bgm-montage\.venv\Scripts\python.exe" server.py
)
if errorlevel 1 pause
