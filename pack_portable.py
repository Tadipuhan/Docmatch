"""Build and verify complete DocMatch portable archives without modifying dist/DocMatch.

Usage (after PyInstaller onedir build):
    python pack_portable.py
    python pack_portable.py --no-7z
    python pack_portable.py --skip-7z-archive

The ZIP uses standard DEFLATE for Windows Explorer compatibility.
If 7-Zip is installed, it additionally builds a solid LZMA2 .7z archive.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def find_7zip() -> str | None:
    custom = os.getenv("DOCMATCH_7ZIP_PATH", "").strip().strip('"')
    if custom and Path(custom).is_file():
        return custom
    for name in ("7z", "7zz", "7za", "7z.exe"):
        found = shutil.which(name)
        if found:
            return found
    for envvar in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(envvar)
        if not base:
            continue
        for suffix in ("7-Zip/7z.exe", "Programs/7-Zip/7z.exe"):
            path = Path(base) / suffix
            if path.is_file():
                return str(path)
    return None


def inventory(folder: Path) -> list[str]:
    return sorted(p.relative_to(folder.parent).as_posix()
                  for p in folder.rglob("*") if p.is_file())


def standard_zip(folder: Path, archive: Path, files: list[str]) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as zf:
        for name in files:
            zf.write(folder.parent / name, name, compress_type=zipfile.ZIP_DEFLATED,
                     compresslevel=9)


def run_7zip(cmd: list[str], cwd: Path) -> None:
    print("[Kompresi]", " ".join(cmd[:2]), "...")
    subprocess.run(cmd, cwd=cwd, check=True)


def verify_zip(archive: Path, expected: list[str]) -> None:
    with zipfile.ZipFile(archive) as zf:
        actual = sorted(n.replace("\\", "/") for n in zf.namelist() if not n.endswith("/"))
        if actual != expected:
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            raise RuntimeError(f"ZIP tidak lengkap: missing={missing[:10]}, extra={extra[:10]}")
        failed = zf.testzip()
        if failed is not None:
            raise RuntimeError(f"CRC ZIP gagal pada {failed}")


def verify_7z(executable: str, archive: Path, expected: list[str], cwd: Path) -> None:
    run_7zip([executable, "t", str(archive), "-y", "-bd"], cwd)
    proc = subprocess.run([executable, "l", "-slt", str(archive)], cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", errors="replace", check=True)
    # The first block is the archive header; entries come after '----------'.
    parts = proc.stdout.split("----------", 1)
    if len(parts) != 2:
        raise RuntimeError("Tidak bisa membaca daftar file arsip 7z")
    current = {}
    found = []
    for line in list(parts[1].splitlines()) + [""]:
        line = line.strip()
        if not line:
            if current.get("Path") and current.get("Folder") != "+":
                found.append(current["Path"].replace("\\", "/"))
            current = {}
            continue
        if " = " in line:
            k, v = line.split(" = ", 1)
            current[k] = v
    if sorted(found) != expected:
        missing = sorted(set(expected) - set(found))
        extra = sorted(set(found) - set(expected))
        raise RuntimeError(f"7z tidak lengkap: missing={missing[:10]}, extra={extra[:10]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive full DocMatch onedir build")
    parser.add_argument("--dist", type=Path, default=Path(__file__).resolve().parent / "dist")
    parser.add_argument("--no-7z", action="store_true", help="Use Python standard ZIP compressor")
    parser.add_argument("--skip-7z-archive", action="store_true", help="Generate ZIP only")
    args = parser.parse_args()

    dist = args.dist.resolve()
    folder = dist / "DocMatch"
    if not (folder / "DocMatch.exe").is_file():
        print("[ERROR] dist\\DocMatch\\DocMatch.exe tidak ditemukan", file=sys.stderr)
        return 1
    if not (folder / "_internal").is_dir():
        print("[ERROR] Folder _internal tidak ditemukan", file=sys.stderr)
        return 1

    files = inventory(folder)
    if not files:
        print("[ERROR] Folder build kosong", file=sys.stderr)
        return 1
    total_bytes = sum((dist / name).stat().st_size for name in files)
    print(f"[DocMatch] Memaketkan {len(files)} file, {total_bytes / 2**20:.1f} MiB. Semua file dipertahankan.", flush=True)

    seven = None if args.no_7z else find_7zip()
    archive_zip = dist / "DocMatch_Portable.zip"
    archive_seven = dist / "DocMatch_Portable.7z"
    # Create each archive as a temporary sibling; the previous result is kept if packing fails.
    tmp_zip = dist / "DocMatch_Portable.tmp.zip"
    tmp_seven = dist / "DocMatch_Portable.tmp.7z"
    for name in (tmp_zip, tmp_seven):
        if name.exists():
            name.unlink()

    try:
        print("[DocMatch] Membuat ZIP standar (Windows Explorer compatible)...", flush=True)
        if seven:
            run_7zip([seven, "a", "-tzip", "-mm=Deflate", "-mx=9",
                      "-mfb=258", "-mpass=15", "-mmt=on", "-y", "-bd",
                      str(tmp_zip), "DocMatch"], dist)
        else:
            print("[INFO] 7-Zip tidak ditemukan; memakai Python ZIP level 9.", flush=True)
            standard_zip(folder, tmp_zip, files)
        verify_zip(tmp_zip, files)
        tmp_zip.replace(archive_zip)
        print(f"[OK] ZIP: {archive_zip} ({archive_zip.stat().st_size / 2**20:.1f} MiB)", flush=True)

        if seven and not args.skip_7z_archive:
            print("[DocMatch] Membuat 7z solid LZMA2 (opsi kompresi lebih tinggi)...", flush=True)
            run_7zip([seven, "a", "-t7z", "-m0=lzma2", "-mx=9", "-ms=on",
                      "-mmt=on", "-y", "-bd", str(tmp_seven), "DocMatch"], dist)
            verify_7z(seven, tmp_seven, files, dist)
            tmp_seven.replace(archive_seven)
            print(f"[OK] 7z:  {archive_seven} ({archive_seven.stat().st_size / 2**20:.1f} MiB)", flush=True)
        elif not seven:
            print("[INFO] Untuk kompresi lebih tinggi, pasang 7-Zip; format .7z akan dibuat pada build berikutnya.")

        print("[OK] Seluruh file dist\\DocMatch disertakan, arsip teruji, dist asli tidak diubah.", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"[ERROR] Pengarsipan gagal: {exc}", file=sys.stderr)
        return 1
    finally:
        for name in (tmp_zip, tmp_seven):
            if name.exists():
                name.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
