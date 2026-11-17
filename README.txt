Fictor IT Tools - Aero Edition (Windows 10/11 x64, Python 3.10+, requer WebView2 - ja vem no Win10/11)
Executar sem compilar: python -m pip install -r requirements.txt ; python techsuite.py
Compilar: python -m pip install -r requirements.txt
          python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --add-data "ui;ui" --name FictorITTools techsuite.py
(ou duplo clique em build.bat). Resultado: dist\RuiTechSuite.exe
Sensores completos: manter o LibreHardwareMonitor aberto.
