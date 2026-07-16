@echo off
title DeepTutor Apply Model Routing Config
cd /d D:\DeepTutor_full

echo ============================================
echo  Apply per-capability model routing config
echo ============================================
echo.

echo [1/2] Copying agents.yaml (Chat/Research=Flash, DeepSolve=Pro)...
copy /Y "templates\agents.yaml" "data\user\settings\agents.yaml" > nul
echo   [OK] agents.yaml configured

echo [2/2] Copying main.yaml (memory compression)...
copy /Y "templates\main.yaml" "data\user\settings\main.yaml" > nul
echo   [OK] main.yaml configured

echo.
echo Restarting container to apply config...
docker compose --env-file data\user\settings\docker.env restart deeptutor
if %ERRORLEVEL% NEQ 0 (
    echo   [FAIL] Restart failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo [OK] Config applied!
echo.
echo Open browser: http://localhost:3782
echo   Go to Settings and add DeepSeek API Key
echo   Model: deepseek-v4-flash (default)
echo ============================================
echo.
pause
