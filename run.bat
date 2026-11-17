@echo off
setlocal enabledelayedexpansion

:: Set working directory to project root
cd /d "%~dp0"

cls
echo ====================================================================
echo                 AgentPay-Guard Unified Launcher
echo ====================================================================
echo.

:: ---------------------------------------------------------------------
:: 0. Check Environment Prerequisites
:: ---------------------------------------------------------------------
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not found in your PATH. Please install Node.js v18+.
    pause
    exit /b 1
)

:: Check for backend virtual environment
set VENV_ACTIVATE=""
if exist "%~dp0backend\venv\Scripts\activate.bat" (
    set VENV_ACTIVATE="%~dp0backend\venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
    set VENV_ACTIVATE="%~dp0.venv\Scripts\activate.bat"
)

:: ---------------------------------------------------------------------
:: 1. Start Local Hardhat Blockchain Node
:: ---------------------------------------------------------------------
echo [1/4] Starting Local Hardhat Blockchain Node (port 8545)...
start "AgentPay - Hardhat Node" cmd /k "title AgentPay - Hardhat Node && cd /d "%~dp0" && npx hardhat node"

echo Waiting for Hardhat node to initialize...
powershell -NoProfile -Command "for ($i=0; $i -lt 30; $i++) { try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8545); $client.Close(); exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Hardhat node port 8545 is not responding yet. Proceeding with deployment attempt...
) else (
    echo [OK] Hardhat node is running and accepting RPC requests.
)

:: ---------------------------------------------------------------------
:: 2. Deploy Smart Contract & Fund Wallet
:: ---------------------------------------------------------------------
echo.
echo [2/4] Deploying AgentGuardWallet contract to local network...
call npx hardhat run scripts/deploy.js --network localhost
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Contract deployment script reported an issue.
    echo You may check the Hardhat Node window for additional logs.
) else (
    echo [OK] Smart contract deployed and funded successfully.
)

:: ---------------------------------------------------------------------
:: 3. Start FastAPI Backend Server
:: ---------------------------------------------------------------------
echo.
echo [3/4] Starting FastAPI Backend server (port 8000)...
if not %VENV_ACTIVATE%=="" (
    start "AgentPay - Backend" cmd /k "title AgentPay - Backend && cd /d "%~dp0backend" && call %VENV_ACTIVATE% && uvicorn app.main:app --reload"
) else (
    start "AgentPay - Backend" cmd /k "title AgentPay - Backend && cd /d "%~dp0backend" && uvicorn app.main:app --reload"
)
echo [OK] Backend server launched.

:: ---------------------------------------------------------------------
:: 4. Start React Frontend (Vite) Server
:: ---------------------------------------------------------------------
echo.
echo [4/4] Starting Vite Frontend dev server (port 5173)...
start "AgentPay - Frontend" cmd /k "title AgentPay - Frontend && cd /d "%~dp0frontend" && npm run dev"
echo [OK] Frontend server launched.

:: Give services a moment to bind ports
powershell -NoProfile -Command "Start-Sleep -Seconds 2"

:: ---------------------------------------------------------------------
:: Interactive Control Panel Loop
:: ---------------------------------------------------------------------
:MENU
cls
echo ====================================================================
echo             AgentPay-Guard Services Are Up and Running!
echo ====================================================================
echo.
echo   [1] Hardhat Local Node : http://127.0.0.1:8545
echo   [2] Smart Contract     : Deployed, Allowlisted ^& Funded
echo   [3] FastAPI Backend    : http://localhost:8000
echo       API Swagger Docs   : http://localhost:8000/docs
echo   [4] Frontend Dashboard : http://localhost:5173
echo.
echo ====================================================================
echo   Controls:
echo     [O] Open Frontend in your default browser
echo     [D] Open API Documentation (/docs)
echo     [S] Stop all running services
echo     [Q] Quit this launcher (keeps background terminals open)
echo ====================================================================
echo.

choice /C ODSQ /N /M "Select an option [O, D, S, Q]: "
if %ERRORLEVEL% equ 1 goto OPEN_FRONTEND
if %ERRORLEVEL% equ 2 goto OPEN_DOCS
if %ERRORLEVEL% equ 3 goto STOP_ALL
if %ERRORLEVEL% equ 4 goto QUIT

:OPEN_FRONTEND
start http://localhost:5173
goto MENU

:OPEN_DOCS
start http://localhost:8000/docs
goto MENU

:STOP_ALL
echo.
echo Stopping all AgentPay-Guard services...
if exist "%~dp0stop.bat" (
    call "%~dp0stop.bat"
) else (
    taskkill /FI "WINDOWTITLE eq AgentPay - *" /F /T >nul 2>&1
    powershell -NoProfile -Command "$ports = @(8545, 8000, 5173); foreach ($port in $ports) { $pids = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique; foreach ($id in $pids) { if ($id -and $id -ne 0 -and $id -ne $PID) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } } }"
)
echo All services stopped.
pause
exit /b 0

:QUIT
echo Exiting launcher. Services continue running in their own windows.
exit /b 0
