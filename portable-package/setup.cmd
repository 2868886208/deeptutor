@echo off
title DeepTutor Setup
echo ============================================
echo  DeepTutor - One-Click Setup
echo ============================================
echo.

:: Check Docker
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker not found.
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo [1/3] Pulling image (one-time, ~2GB)...
docker pull ghcr.io/2868886208/deeptutor:latest
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pull failed. Check your network.
    pause
    exit /b 1
)

:: Copy config
echo [2/3] Setting up config...
mkdir data\user\settings 2>nul
copy /Y config\agents.yaml data\user\settings\agents.yaml >nul
copy /Y config\main.yaml data\user\settings\main.yaml >nul
echo {} > data\user\settings\system.json
echo {} > data\user\settings\integrations.json

:: Start
echo [3/3] Starting DeepTutor...
docker compose down 2>nul
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Start failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Done! DeepTutor is running.
echo.
echo Open: http://localhost:3782
echo Or double-click launcher.bat for desktop mode.
echo.
echo Next: Go to Settings and add your DeepSeek API Key.
echo ============================================
echo.
pause
