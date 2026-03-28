@echo off
setlocal

echo ========================================
echo   Disk Cleaner CLI - Build Script
echo ========================================
echo.

:: Check if running in correct directory
if not exist "pyproject.toml" (
    echo Error: Run this script from the project root directory.
    exit /b 1
)

:: Install the package in development mode
echo [1/4] Installing package in development mode...
pip install -e . --quiet
if errorlevel 1 (
    echo Error: Failed to install package.
    exit /b 1
)
echo.

:: Install PyInstaller if not present
echo [2/4] Checking PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [2/4] Installing PyInstaller...
    pip install pyinstaller --quiet
)
echo.

:: Clean previous builds
echo [3/4] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo.

:: Build the executable
echo [4/4] Building executable...
python -m PyInstaller disk-cleaner.spec --clean
if errorlevel 1 (
    echo Error: Build failed.
    exit /b 1
)
echo.

echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Single executable:
echo   dist\disk-cleaner.exe
echo.
echo Size: ~9 MB
echo.
echo To distribute: Copy the single 'disk-cleaner.exe' file to any Windows computer.
echo.
echo To rebuild, run: build.bat
echo.

endlocal
