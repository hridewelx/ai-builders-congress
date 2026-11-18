@echo off
REM Lotline demo launcher (Windows). Creates the demo database if missing,
REM then serves on http://127.0.0.1:8077
setlocal
set PYTHON=%LOCALAPPDATA%\Programs\Python\pythoncore-3.14-64\python.exe
if not exist "%PYTHON%" set PYTHON=python
cd /d "%~dp0"
if not exist "data\lotline.db" "%PYTHON%" -m app.seed
set LOTLINE_DEMO=1
"%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8077
