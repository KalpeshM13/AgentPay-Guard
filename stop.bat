@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
echo ====================================================================
echo             Stopping All AgentPay-Guard Services
echo ====================================================================
echo.

:: 1. Close command prompt windows titled "AgentPay - *"
taskkill /FI "WINDOWTITLE eq AgentPay - *" /F /T >nul 2>&1

:: 2. Terminate any lingering processes bound to Hardhat (8545), FastAPI (8000), Vite (5173)
powershell -NoProfile -Command ^
  "$ports = @(8545, 8000, 5173); " ^
  "foreach ($port in $ports) { " ^
  "    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue; " ^
  "    if ($conns) { " ^
  "        $pids = $conns.OwningProcess | Select-Object -Unique; " ^
  "        foreach ($id in $pids) { " ^
  "            if ($id -and $id -ne 0 -and $id -ne $PID) { " ^
  "                Write-Host \"Freeing port $port (PID: $id)...\"; " ^
  "                Stop-Process -Id $id -Force -ErrorAction SilentlyContinue; " ^
  "            } " ^
  "        } " ^
  "    } " ^
  "}"

echo.
echo [OK] All AgentPay-Guard processes on ports 8545, 8000, and 5173 have been stopped.
echo ====================================================================
