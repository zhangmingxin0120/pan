@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "APP_NAME=Pan"
set "APP_URL=http://localhost:8091"
set "HEALTH_URL=http://localhost:8091/health"
set "FORCE_BUILD=0"
if /I "%~1"=="--build" set "FORCE_BUILD=1"

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker Desktop is not installed or docker is not in PATH.
  echo Install Docker Desktop, then run this script again.
  pause
  exit /b 1
)

docker info >nul 2>nul
if not errorlevel 1 goto :docker_ready

echo Docker Desktop is not running. Starting it now...
if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
  powershell -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden"
) else if exist "%LOCALAPPDATA%\Docker\Docker Desktop.exe" (
  powershell -NoProfile -Command "Start-Process -FilePath '%LOCALAPPDATA%\Docker\Docker Desktop.exe' -WindowStyle Hidden"
) else (
  echo [ERROR] Docker Desktop executable was not found.
  pause
  exit /b 1
)

set /a docker_attempts=0
:wait_docker
set /a docker_attempts+=1
docker info >nul 2>nul
if not errorlevel 1 goto :docker_ready
if !docker_attempts! GEQ 60 (
  echo [ERROR] Docker did not become ready within two minutes.
  pause
  exit /b 1
)
powershell -NoProfile -Command "Start-Sleep -Seconds 2"
goto :wait_docker

:docker_ready
if not exist ".env" if exist ".env.example" copy /Y ".env.example" ".env" >nul
echo [1/3] Validating Docker Compose...
docker compose config >nul
if errorlevel 1 goto :failed

if "%FORCE_BUILD%"=="1" goto :build_images

echo [2/3] Starting existing images...
docker compose up -d --no-build
if not errorlevel 1 (
  set "WAIT_STEP=[3/3]"
  goto :wait_application
)

echo Existing images are unavailable. A build is required.

:build_images
echo [2/4] Building images (network failures will be retried)...
set /a build_attempts=0
:retry_build
set /a build_attempts+=1
docker compose build
if not errorlevel 1 goto :build_ready
if !build_attempts! GEQ 3 (
  echo [ERROR] Image build failed after three attempts.
  echo The configured mirror may be temporarily unavailable.
  echo You can change PYTHON_IMAGE, NODE_IMAGE and NGINX_IMAGE in .env.
  pause
  exit /b 1
)
echo Build attempt !build_attempts! failed. Retrying in 5 seconds...
powershell -NoProfile -Command "Start-Sleep -Seconds 5"
goto :retry_build

:build_ready
echo [3/4] Starting rebuilt images...
docker compose up -d --no-build
if errorlevel 1 goto :failed
set "WAIT_STEP=[4/4]"

:wait_application
echo %WAIT_STEP% Waiting for the application...
set /a health_attempts=0
:wait_health
set /a health_attempts+=1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%HEALTH_URL%' -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { exit 0 } } catch {}; exit 1"
if not errorlevel 1 goto :ready
if !health_attempts! GEQ 40 goto :failed
powershell -NoProfile -Command "Start-Sleep -Seconds 2"
goto :wait_health
:ready
echo.
echo %APP_NAME% is ready: %APP_URL%
if /I not "%PAN_NO_OPEN%"=="1" start "" "%APP_URL%"
exit /b 0
:failed
echo.
echo [ERROR] Startup failed. Recent logs:
docker compose logs --tail=100
pause
exit /b 1
