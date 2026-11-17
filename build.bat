@echo off
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --add-data "ui;ui" --name FictorITTools techsuite.py
echo.
echo EXE em dist\FictorITTools.exe
pause
