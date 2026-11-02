# DocMatch v0.5 — Portable Windows build kit

This is **source code and a Windows build script**, not a prebuilt executable and **does not contain LibreOffice binaries**. Build on a Windows PC with Python and a legitimate LibreOffice installation. End users can then run the complete output folder without installing LibreOffice or Python separately (subject to Windows compatibility).

## Build (PowerShell on Windows)

1. Install Python and LibreOffice on the **build computer**.
2. Open PowerShell in this directory.
3. Run `powershell -ExecutionPolicy Bypass -File .\build_portable_windows.ps1`.
4. Distribute the complete `dist\DocMatch` directory. Run `DocMatch.exe` from inside it.

If LibreOffice is elsewhere: `powershell -ExecutionPolicy Bypass -File .\build_portable_windows.ps1 -LibreOfficePath "D:\Apps\LibreOffice"`.

The build script copies the installed LibreOffice directory into `dist\DocMatch\runtime\libreoffice`. Do **not** copy only `soffice.exe`: its libraries, share data and other resources are required. Verify that the LibreOffice installation being bundled works as a self-contained runtime; a normal installation copied to another PC may have additional runtime/registry dependencies. Test on a clean Windows VM without LibreOffice or Python installed.

**Licensing:** LibreOffice is third-party software. Include appropriate LibreOffice license and notices and comply with the applicable redistribution terms. This build script does not supply or fetch LibreOffice.

## Source-mode testing

`py -m pip install -r requirements.txt`

`py docmatch.py`

For an alternative executable location, set `DOCMATCH_SOFFICE` to its full path.

## Changes

- `portable_runtime.py`: locate bundled runtime first, then Windows installation, then PATH.
- `legacy_v01.py`: use the runtime resolver for DOC/DOCX conversions.
- `docmatch.py` and `legacy_v01.py`: replace deprecated `import fitz` with `import pymupdf as fitz`.
- `build_portable_windows.ps1`: build PyInstaller onedir and stage LibreOffice.

**Limitations:** This is a build kit, not a verified end-user release. GUI and DOC conversion must be validated on Windows. The original v0.4 document comparison and annotation limitations remain.
