@echo off
rem Builds a standalone dist\EggRushHarry.exe (no Python needed to play it).
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name EggRushHarry main.py
echo.
echo Done: dist\EggRushHarry.exe
