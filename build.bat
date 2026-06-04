@echo off
setlocal

echo ========================================
echo   Disk Cleaner CLI - Build Script
echo ========================================
echo.

:: Check if running in the correct directory
if not exist "pyproject.toml" (
    echo Error: Run this script from the project root directory.
    exit /b 1
)

:: Install the package with dev extras (pytest, etc.)
echo [1/5] Installing package with dev extras...
pip install -e ".[dev]" --quiet
if errorlevel 1 (
    echo Error: Failed to install package.
    exit /b 1
)
echo.

:: Install PyInstaller if not present
echo [2/5] Checking PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [2/5] Installing PyInstaller...
    pip install pyinstaller --quiet
    if errorlevel 1 (
        echo Error: Failed to install PyInstaller.
        exit /b 1
    )
)
echo.

:: Clean previous builds
echo [3/5] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo.

:: Build the executable
echo [4/5] Building executable...
python -m PyInstaller disk-cleaner.spec --clean
if errorlevel 1 (
    echo Error: Build failed.
    exit /b 1
)
echo.

:: Run tests as a sanity check
echo [5/5] Running test suite...
python -m pytest tests/ -q
if errorlevel 1 (
    echo Warning: Tests failed. The executable was built, but please review the failures.
)
echo.

echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Single executable: dist\disk-cleaner.exe
echo.
echo To distribute: Copy the single 'disk-cleaner.exe' file to any Windows computer.
echo.
echo To rebuild, run: build.bat
echo.

endlocal
