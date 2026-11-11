DocMatch v1.6 - GSL Attached List page mapping (partial fix, no OCR)

- GSL uses 3 PDF pages: page 1 main SWB, page 2 empty image-only spacer, page 3 Attached List.
- Page 3 is now separated into Header, Container & Seal, Cargo Description, Weight & Measurement, and Clauses.
- Page 2 is not considered a missing Attached List; its absence of text is expected.
- Missing page 3 now raises an explicit error.
- Fields whose Type3 glyphs are not recoverable are skipped with a warning. They are NOT reported as matching.

IMPORTANT: On both supplied GSL PDFs, the Type3 font of page 3 still has glyphs that cannot be decoded with confidence. This patch does NOT claim complete comparison of page 3. Further verified glyph mapping or a PDF with valid Unicode text is needed for full coverage, without OCR.

INSTALL: Backup docmatch.py and waybill_rules.py. Extract all files, keep your existing rules.py, then rebuild portable using build_portable.bat on Windows.
