@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "HOST=0.0.0.0"
set "PORT=18317"

cd /d "%ROOT_DIR%" || goto :error

where uv >nul 2>nul
if errorlevel 1 (
  echo [ERROR] uv is not installed or not in PATH.
  echo Install uv first: https://docs.astral.sh/uv/
  goto :error
)

echo [INFO] Checking existing CPA Helper process on port %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$port = %PORT%; $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue; if (-not $connections) { exit 0 }; $processIds = @($connections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -ne 0 }); foreach ($processId in $processIds) { $proc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $processId) -ErrorAction SilentlyContinue; $cmd = if ($proc) { [string]$proc.CommandLine } else { '' }; if ($cmd -match 'uvicorn' -and $cmd -match 'app\.main:app' -and $cmd -match '--port\s+%PORT%') { Write-Host ('[INFO] Stopping existing CPA Helper process PID ' + $processId + '...'); Stop-Process -Id $processId -Force; continue }; Write-Host ('[ERROR] Port ' + $port + ' is occupied by another process PID ' + $processId + '.'); if ($cmd) { Write-Host $cmd }; exit 2 }; for ($i = 0; $i -lt 20; $i++) { Start-Sleep -Milliseconds 500; if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) { exit 0 } }; Write-Host ('[ERROR] Port ' + $port + ' is still in use after stopping CPA Helper.'); exit 3"
if errorlevel 1 goto :error

if not exist "%FRONTEND_DIR%\dist\index.html" (
  echo [INFO] Frontend build not found. Building frontend...
  where npm >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH.
    goto :error
  )
  cd /d "%FRONTEND_DIR%" || goto :error
  if not exist "node_modules" call npm install || goto :error
  call npm run build || goto :error
)

cd /d "%BACKEND_DIR%" || goto :error

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Backend virtual environment not found. Syncing dependencies...
  uv sync || goto :error
)

echo [INFO] Applying database migrations...
uv run alembic upgrade head || goto :error

echo.
echo CPA Helper is starting on http://127.0.0.1:%PORT%
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } ^| Select-Object -First 1 -ExpandProperty IPAddress)"`) do set "LAN_IP=%%I"
if defined LAN_IP echo LAN URL: http://%LAN_IP%:%PORT%
echo.
echo Keep this window open while using CPA Helper.
echo Press Ctrl+C to stop the server.
echo.

uv run -m uvicorn app.main:app --host %HOST% --port %PORT%
goto :end

:error
echo.
echo Startup failed. Check the messages above.
pause
exit /b 1

:end
endlocal


