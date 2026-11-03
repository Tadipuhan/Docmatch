@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo Folder .venv belum ditemukan. Menggunakan Python 3.15 yang terpasang.
    py -3.15 main.py
)
if errorlevel 1 (
    echo.
    echo Aplikasi gagal berjalan. Periksa pesan error di atas.
    pause
)
