@echo off
setlocal
cd /d "%~dp0"
echo [DocMatch] Pemeriksaan logo dan file sumber...
for %%I in (assets\docmatch.ico assets\docmatch_logo.png assets\docmatch_128.png) do (
  if not exist "%%I" (
    echo [ERROR] Logo/ikon %%I tidak ditemukan.
    pause
    exit /b 1
  )
)
for %%F in (docmatch.py legacy_v01.py waybill_rules.py editor.py rules.py) do (
  if not exist "%%F" (
    echo [ERROR] File %%F tidak ditemukan. Build dibatalkan.
    echo Salin %%F dari project DocMatch yang sudah berjalan.
    pause
    exit /b 1
  )
)
py -3 -m venv .venv
if errorlevel 1 goto failed
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
python -m compileall -q docmatch.py legacy_v01.py waybill_rules.py editor.py rules.py
if errorlevel 1 (
  echo [ERROR] Sintaks source tidak valid. Build dibatalkan.
  goto failed
)
python -c "import legacy_v01, rules, waybill_rules, editor; print('[OK] Modul internal bisa diimpor')"
if errorlevel 1 (
  echo [ERROR] Import modul internal gagal. Build dibatalkan.
  goto failed
)
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DocMatch --icon assets\docmatch.ico --add-data "assets;assets" --collect-all pymupdf --hidden-import legacy_v01 --hidden-import rules --hidden-import waybill_rules --hidden-import editor docmatch.py
if errorlevel 1 goto failed
if not exist "dist\DocMatch\DocMatch.exe" goto failed
if not exist "dist\DocMatch\_internal\assets\docmatch.ico" (
  echo [ERROR] Ikon tidak ikut ke paket portable.
  goto failed
)
if not exist "dist\DocMatch\_internal\assets\docmatch_logo.png" (
  echo [ERROR] Logo tidak ikut ke paket portable.
  goto failed
)
python -c "from pathlib import Path; p=Path('dist/DocMatch/_internal'); names=['legacy_v01','rules','waybill_rules','editor']; print('Build tersedia:',p.exists()); print('Periksa semua modul saat uji .exe di Windows')"
echo.
echo [OK] Hasil: dist\DocMatch\DocMatch.exe
pause
exit /b 0
:failed
echo [ERROR] Build gagal. Periksa pesan di atas.
pause
exit /b 1
