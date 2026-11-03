DocMatch v1.5 — SWB carrier presets (offline)

INSTALL
1. Backup existing docmatch.py and waybill_rules.py.
2. Copy docmatch.py and waybill_rules.py to your project root; keep existing legacy_v01.py, rules.py, editor.py.
3. Copy assets/ to your project root (preserves the latest DM branding).
4. Run: py docmatch.py

CHANGES
- Waybill renamed to SWB - ANL/CNC/CMA CGM (same ANL extraction coordinates).
- Added SWB - EVERGREEN with template-specific regions, based on supplied EVG PDF.
- Added SWB - Golden Star Line with template-specific regions and a text-encoding safety check.
- JSON reports record waybill_preset.

IMPORTANT LIMITATIONS
- Evergreen regions are initial calibration from one sample, not production-validated.
- GSL supplied PDF has unreadable font encoding in PyMuPDF. The app deliberately blocks comparisons on such files rather than fabricate differences. OCR was NOT added.
- For each comparison, both files must have the same carrier layout.
- Field extraction is still coordinate-based; labels/overlaps and multi-page cargo need additional calibration with paired reference/examined examples.
- Existing export/editor features remain in the source but were not GUI-tested on Windows.

VALIDATION: Python syntax, Evergreen self-comparison, GSL encoding guard.
