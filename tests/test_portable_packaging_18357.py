"""Smoke tests for v1.8.35.7 portable packing (without requiring Windows/7-Zip)."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack_portable.py"


class TestPortablePackaging(unittest.TestCase):
    def test_full_inventory_in_standard_zip_and_no_dist_deletion(self):
        with tempfile.TemporaryDirectory() as temp:
            dist = Path(temp) / "dist"
            root = dist / "DocMatch"
            (root / "_internal" / "tesseract" / "tessdata").mkdir(parents=True)
            (root / "_internal" / "Qt6").mkdir()
            data = {
                "DocMatch.exe": b"dummy-exe" * 140,
                "_internal/Qt6/Qt6Core.dll": b"dummy-qt" * 500,
                "_internal/tesseract/tesseract.exe": b"dummy-ocr" * 250,
                "_internal/tesseract/tessdata/eng.traineddata": b"dummy-english" * 400,
            }
            for name, contents in data.items():
                (root / name).write_bytes(contents)
            before = {name: (root / name).read_bytes() for name in data}
            result = subprocess.run([sys.executable, str(PACK), "--dist", str(dist), "--no-7z"],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archive = dist / "DocMatch_Portable.zip"
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as z:
                expected = {f"DocMatch/{k}" for k in data}
                self.assertEqual(set(z.namelist()), expected)
                self.assertIsNone(z.testzip())
                for key, contents in data.items():
                    self.assertEqual(z.read(f"DocMatch/{key}"), contents)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in data})

    def test_missing_exe_must_fail_without_creating_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            dist = Path(temp) / "dist"
            (dist / "DocMatch" / "_internal").mkdir(parents=True)
            result = subprocess.run([sys.executable, str(PACK), "--dist", str(dist), "--no-7z"],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((dist / "DocMatch_Portable.zip").exists())


if __name__ == "__main__":
    unittest.main()
