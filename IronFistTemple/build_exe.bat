@echo off
rem Builds a standalone dist\IronFistTemple.exe (no Python needed to play it).
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name IronFistTemple main.py
echo.
echo Done: dist\IronFistTemple.exe
