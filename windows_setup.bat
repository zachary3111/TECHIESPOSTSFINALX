@echo off
echo Setting up Facebook Posts Search Scraper for Windows...
echo =====================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found - creating virtual environment...

REM Create virtual environment
python -m venv facebook_scraper_env

REM Activate virtual environment
call facebook_scraper_env\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
pip install playwright==1.40.0 beautifulsoup4==4.12.2 aiofiles==23.2.1

REM Install Playwright browsers
echo Installing Playwright browsers...
playwright install chromium

echo.
echo Setup completed successfully!
echo.
echo To use the scraper:
echo 1. Activate environment: facebook_scraper_env\Scripts\activate.bat
echo 2. Run scraper: python facebook_scraper.py
echo.
echo Press any key to exit...
pause >nul