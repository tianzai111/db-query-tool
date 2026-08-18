# ============================================================================
#  One-click demo launcher (Windows / PowerShell)
#
#  This script:
#    1. Creates a Python virtual environment (if missing) and installs deps
#    2. Seeds the zero-install SQLite demo database and registers it
#    3. Starts the FastAPI backend (http://localhost:8000)
#
#  The frontend needs Node.js. If `npm` is available it will be installed and
#  started in a second window on http://localhost:5173.
#
#  Usage:  right-click -> "Run with PowerShell", or:
#          powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
# ============================================================================

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Write-Step($msg) { Write-Host "`n[demo] $msg" -ForegroundColor Cyan }

# --- Locate Python -----------------------------------------------------------
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $Python) {
    Write-Host "Python was not found on PATH. Please install Python 3.12+." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python: $Python"

# --- Backend virtualenv ------------------------------------------------------
$Venv = Join-Path $Backend ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Step "Creating virtual environment..."
    & $Python -m venv $Venv
}
Write-Step "Installing backend dependencies (Tsinghua mirror)..."
& $VenvPython -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
& $VenvPython -m pip install -e "$Backend[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# --- Seed demo DB ------------------------------------------------------------
Write-Step "Seeding demo database (SQLite)..."
$env:OPENAI_API_KEY = "demo-key-not-real"
& $VenvPython (Join-Path $Backend "scripts\setup_demo.py")

# --- Start backend -----------------------------------------------------------
Write-Step "Starting backend on http://localhost:8000 ..."
$backendProc = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000" `
    -WorkingDirectory $Backend -PassThru

# --- Start frontend (optional) ----------------------------------------------
$npm = (Get-Command npm -ErrorAction SilentlyContinue).Source
if ($npm) {
    if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
        Write-Step "Installing frontend dependencies (this may take a minute)..."
        Push-Location $Frontend
        & $npm install --registry=https://registry.npmmirror.com
        Pop-Location
    }
    Write-Step "Starting frontend on http://localhost:5173 ..."
    Start-Process -FilePath $npm -ArgumentList "run","dev" -WorkingDirectory $Frontend
    Start-Sleep -Seconds 3
    Write-Host "`n==================================================================" -ForegroundColor Green
    Write-Host " Demo is running!" -ForegroundColor Green
    Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Green
    Write-Host "   Backend : http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "   A 'demo' database is pre-registered. Run a query and try Export!" -ForegroundColor Green
    Write-Host "==================================================================" -ForegroundColor Green
} else {
    Write-Host "npm not found - only the backend is running." -ForegroundColor Yellow
    Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Yellow
}

Write-Host "`nPress Ctrl+C in the backend window to stop, or close this window." -ForegroundColor Yellow
try { Wait-Process -Id $backendProc.Id } catch {}
