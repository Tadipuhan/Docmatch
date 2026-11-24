# Changelog v1.8.35.7

- Auto ZIP packaging after `build_portable.bat` completes.
- High compression with 7-Zip ZIP Deflate; optional native 7z LZMA2 solid.
- Fallback standard library ZIP if 7-Zip unavailable.
- Archive verification: entries, CRC, and 7z test.
- Portable dist content unchanged, no file exclusion/deletion.
- Runtime PDF extraction/annotations/OCR/correction logic unchanged from 1.8.35.6.
- Requires Windows validation of final archive size and `DocMatch.exe` startup.
