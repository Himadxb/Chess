@echo off
title React Chess Launcher

echo ==========================================
echo         React Chess - Launcher
echo ==========================================
echo.

:: Check if Node.js is installed
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Node.js not found. Attempting to install automatically...
    echo.

    :: Try installing via winget (available on Windows 10/11)
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        echo [INFO] Installing Node.js via winget...
        winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
        if %errorlevel% neq 0 (
            echo [ERROR] Automatic install failed.
            goto :manualinstall
        )
        echo [OK] Node.js installed! Please re-run this file.
        pause
        exit /b 0
    ) else (
        goto :manualinstall
    )
)

echo [OK] Node.js found:
node -v
goto :start

:manualinstall
echo [ERROR] Could not auto-install Node.js.
echo Please download and install it manually from:
echo        https://nodejs.org
echo.
pause
exit /b 1

:start
:: Install dependencies if node_modules doesn't exist
if not exist "node_modules\" (
    echo.
    echo [INFO] Installing dependencies for the first time, this may take a minute...
    npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed!
)

echo.
echo [INFO] Starting the app...
echo [INFO] Opening http://localhost:5173 in your browser...
echo.

:: Open browser after a short delay
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:5173"

:: Start the dev server
npm run dev

pause
