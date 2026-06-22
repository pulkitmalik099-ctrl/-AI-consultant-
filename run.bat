@echo off
setlocal EnableDelayedExpansion

title AI Consultant Knowledge Copilot

echo.
echo  =====================================================
echo   AI Consultant Knowledge Copilot
echo  =====================================================
echo.

:: ── Project root (same folder as this .bat file) ──────────────────────────
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: ── Python check ──────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  Python %PY_VER% detected.

:: ── Virtual environment ───────────────────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo  Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
)

call .venv\Scripts\activate.bat
echo  Virtual environment activated.

:: ── Install / upgrade dependencies ────────────────────────────────────────
echo.
echo  Checking dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo  [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
echo  Dependencies OK.

:: ── .env check ────────────────────────────────────────────────────────────
echo.
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo  [NOTICE] .env created from .env.example.
        echo  [ACTION] Open .env and set your OPENAI_API_KEY before using the app.
        echo.
        notepad .env
        echo  Press any key once you have saved your API key in .env...
        pause >nul
    ) else (
        echo  [WARNING] No .env file found. Create one with OPENAI_API_KEY=sk-...
    )
) else (
    :: Check if API key is still the placeholder
    findstr /C:"sk-..." .env >nul 2>&1
    if not errorlevel 1 (
        echo  [WARNING] .env still contains the placeholder key.
        echo  [ACTION]  Edit .env and replace sk-... with your real OPENAI_API_KEY.
        echo.
        notepad .env
        echo  Press any key to continue after saving...
        pause >nul
    )
)

:: ── Create required directories ───────────────────────────────────────────
if not exist "data\documents" mkdir "data\documents"
if not exist "data\zendesk"   mkdir "data\zendesk"
if not exist "data\jira"      mkdir "data\jira"
if not exist "logs"           mkdir "logs"

:: ── Start server ──────────────────────────────────────────────────────────
echo.
echo  =====================================================
echo   Starting server at http://localhost:8000
echo   Chat UI  ->  http://localhost:8000
echo   API Docs ->  http://localhost:8000/docs
echo   Press Ctrl+C to stop
echo  =====================================================
echo.

:: Open browser after a short delay (runs in background)
start "" cmd /c "timeout /t 3 >nul && start http://localhost:8000"

:: Start uvicorn
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo  Server stopped.
pause
