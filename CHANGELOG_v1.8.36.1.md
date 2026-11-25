# DocMatch v1.8.36.1 — PL + SI Upload Callback Fix

## Bug fixed

- Fixed **Pilih Jenis Dokumen Rujukan → PL + SI**: both filenames appeared after selection but clicking **OK** incorrectly displayed **“Upload kedua file PDF SI dan PL.”**
- Root cause: `QPushButton.clicked(bool)` injected its `checked` value into the first positional argument of the nested `choose_pdf(k=key, ...)` callback. As a result, the selected file paths were stored under boolean dictionary keys instead of `selected['pl']` / `selected['si']`.
- The callback now accepts `_checked` separately and captures `k` and `label` using keyword-only defaults. The UI filename and the internal path now refer to the same selected file.
- Keeps the original SWB reference mode, PL/SI parsers, compare engine, correction notes, and portable build scripts intact.

## Installation

Replace `docmatch.py` in your v1.8.36.0 source folder with the version from this release, or extract the complete source ZIP into a new folder. If you use the portable EXE, rebuild with `build_portable.bat`.

## Testing

- Regression test reproduces the original Qt `clicked(bool)` dispatch for both PL and SI and verifies the filenames and stored paths.
- This release was source-tested on Linux. A real Windows GUI/portable build was not executed here.
