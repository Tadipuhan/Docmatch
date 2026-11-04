@echo off
setlocal
cd /d "%~dp0"
if not exist "rules.py" (
 echo [ERROR] rules.py tidak tersedia. Salin rules.py dari project DocMatch yang sudah berjalan.
 pause
 exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto failed
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DocMatch --icon assets\docmatch.ico --add-data "assets;assets" --collect-all pymupdf --hidden-import fitz docmatch.py
if errorlevel 1 goto failed
echo.
echo [OK] Hasil: dist\DocMatch\DocMatch.exe
pause
exit /b 0
:failed
echo [ERROR] Build gagal. Periksa pesan di atas.
pause
exit /b 1
