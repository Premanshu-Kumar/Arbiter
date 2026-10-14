@echo off
echo ========================================
echo Excel Add-in Setup Script
echo ========================================
echo.

echo Checking prerequisites...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js installed successfully
echo.

echo Installing dependencies...
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Installing additional packages...
call npm install react react-dom @types/react @types/react-dom
call npm install office-js
call npm install webpack webpack-cli ts-loader
call npm install --save-dev @types/office-js

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Run: npm run build
echo 2. Start local server: npx http-server . -p 3000
echo 3. Open Excel and load manifest.xml
echo.
echo For detailed instructions, see README.md
echo.
pause
