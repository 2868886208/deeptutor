@echo off
title DeepTutor Docker Build and Start
cd /d D:\DeepTutor_full

echo ============================================
echo  DeepTutor v1.5.1 Build and Start
echo  per-capability model routing enabled
echo ============================================
echo.
echo [1/2] Creating directories...
if not exist "data\user\settings" mkdir data\user\settings
if not exist "data\user\settings\docker.env" (
    echo DEEPTUTOR_DOCKER_BACKEND_PORT=8001 > data\user\settings\docker.env
    echo DEEPTUTOR_DOCKER_FRONTEND_PORT=3782 >> data\user\settings\docker.env
    echo DEEPTUTOR_DOCKER_POCKETBASE_PORT=8090 >> data\user\settings\docker.env
)

echo [2/2] Building Docker image (10-15 minutes)...
echo.
docker compose --env-file data\user\settings\docker.env build --no-cache
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [FAIL] Build failed. Check errors above.
    pause
    exit /b 1
)

echo.
echo [OK] Build success. Starting containers...
docker compose --env-file data\user\settings\docker.env up -d
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [FAIL] Start failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo [OK] DeepTutor is running!
echo.
echo Open browser: http://localhost:3782
echo.
echo Next steps:
echo   1. Open http://localhost:3782
echo   2. Settings - add DeepSeek API Key
echo   3. Run 2-setup-config.cmd to apply model routing
echo ============================================
echo.
pause
