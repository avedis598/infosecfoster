@echo off
echo ========================================================
echo   AML SIEM Application - Windows Executable Builder
echo ========================================================
echo.
echo Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in your PATH. 
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Installing requirements (paramiko, pyinstaller)...
pip install paramiko pyinstaller

echo.
echo Building single executable...
:: The --windowed flag hides the terminal window in the background (good for GUIs)
:: The --onefile flag bundles everything into a single .exe
pyinstaller --noconfirm --onefile --windowed --name "AMLSiemApp" --add-data "aml_siem;aml_siem" aml_siem\main.py

echo.
if exist "dist\AMLSiemApp.exe" (
    echo ========================================================
    echo   SUCCESS! 
    echo   Your executable is located at:
    echo   dist\AMLSiemApp.exe
    echo ========================================================
) else (
    echo Build failed. Please check the logs above.
)
pause
