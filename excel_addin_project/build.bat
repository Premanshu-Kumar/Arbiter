@echo off
echo ========================================
echo Excel Add-in Build Script
echo ========================================
echo.

echo Building TypeScript project...
call npx tsc
if %errorlevel% neq 0 (
    echo ERROR: TypeScript compilation failed
    pause
    exit /b 1
)

echo.
echo Building with webpack...
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: Webpack build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start local server: npx http-server . -p 3000
echo 2. Open Excel and load manifest.xml
echo.
pause
