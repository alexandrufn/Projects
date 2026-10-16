@echo off
cd /d "%~dp0"
python -c "import pygame" 2>nul || python -m pip install -r requirements.txt
python main.py
