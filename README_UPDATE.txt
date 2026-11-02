DocMatch v0.8 — Hierarchical Discrepancy List (source patch)

Files to replace:
- docmatch.py
- waybill_rules.py

Install: Close DocMatch; back up the existing two files; copy these files into the Python project folder; run: py docmatch.py
Do not copy these .py files into an existing PyInstaller dist folder; an EXE needs rebuilding.

Changes:
- Waybill comparison creates a distinct finding for each SequenceMatcher edit opcode (replace/delete/insert).
- Filter Perubahan/Hilang/Berlebih operates on those individual findings.
- Results tree groups findings by Waybill field and shows counts per type.
- Markers and result rows use the same finding ID after positional sorting.
- Repeated words belonging to one finding show multiple highlights but only one number marker per page.

Limitations:
- SequenceMatcher heuristics can classify large replacements imperfectly, especially in PDF tables.
- PDF text extraction must be manually verified; no OCR is included.
- This is a source patch, not a ready-made EXE or a complete application package.
- GUI has not been tested on Windows in this environment; Python syntax compilation passed.
