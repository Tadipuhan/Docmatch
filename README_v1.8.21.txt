DocMatch v1.8.21 — Hybrid Validation Workspace (Layout 01 + 04 + 05)

Baseline: DocMatch v1.8.20_Hybrid_Manual_Validation. This is a source update,
not a compiled Windows executable.

UI changes in hybrid_validation.py:
- Resizable three-panel layout: field checklist at left, dual PDF viewer in center,
  text and crop inspector at right.
- Progress bar and per-field status colors for all configured field names.
- Parameter next/previous buttons.
- Two crop previews and separate high-resolution crop dialogs.
- Stage-two extraction and manual text correction remain available in the inspector.
- Candidate list and explicit confirmation remain in place; candidate location is
  never assumed correct solely from matching text.
- Selected PDF coordinates, document page and candidate/manual source are shown;
  selection_method is included in exported stage-two records.
- Stage-two JSON schema version 2; existing stage-two record structure supported.
- Stage-one results, overlay logic, OCR recovery and report generation remain unchanged.

Usage:
1. Compare the two files in DocMatch as before.
2. Open Manual Validation — Tahap 2.
3. Choose a parameter from the left pane.
4. Draw an area on PDF A, then run Cari Otomatis di PDF B.
5. Inspect the proposed yellow rectangle on PDF B; correct with mouse if needed.
6. Inspect text and cropped images on the right. Use Perbesar Crop for enlarged view.
7. Confirm the comparison; continue to the next parameter.
8. Export stage-two JSON separately if required.

Known limits:
- Source ZIP does not include rules.py, imported by docmatch.py. Restore the
  original rules.py from your working installation before launching full app.
- No GUI runtime test was possible in this build environment: PySide6 is absent.
- No bundled sample GSL/ANL/CNC PDFs exist in this ZIP for real document tests.
- Scanned regions without a usable text layer are not automatically decoded by
  this UI redesign; existing extraction limitations remain.
- The candidate scoring is unchanged from v1.8.20 and needs validation against
  real shipping documents before being trusted.
