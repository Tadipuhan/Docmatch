param([string]$LibreOfficePath = 'C:\Program Files\LibreOffice')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path "$LibreOfficePath\program\soffice.exe")) { throw "LibreOffice runtime tidak ditemukan di $LibreOfficePath. Pasang LibreOffice di komputer BUILD terlebih dahulu atau tentukan -LibreOfficePath." }
py -m pip install -r requirements.txt pyinstaller
py -m PyInstaller --noconfirm --clean --windowed --onedir --name DocMatch --collect-all pymupdf docmatch.py
$target = Join-Path $PSScriptRoot 'dist\DocMatch\runtime\libreoffice'
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path $LibreOfficePath '*') -Destination $target -Recurse -Force
if (-not (Test-Path "$target\program\soffice.exe")) { throw 'Runtime LibreOffice gagal disalin.' }
Write-Host "Paket portable dibuat di: $PSScriptRoot\dist\DocMatch"
Write-Host 'Distribusikan SELURUH folder dist\DocMatch, bukan DocMatch.exe saja.'
Write-Host 'Sertakan pemberitahuan lisensi LibreOffice dan dependensinya dari distribusi sumber.'
