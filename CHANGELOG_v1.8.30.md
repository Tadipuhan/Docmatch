# CHANGELOG v1.8.30 (Consolidated Development)

- Based on v1.8.29, preserving the comparison, hybrid validation, GSL region, and PDF export behavior.
- Added local atomic `.dmjson` session save / load and SHA-256 source verification.
- Added local delayed autosave and a bounded audit history for stage-two changes and annotation toggles.
- Added clean-render HiDPI LRU cache (3 pages per viewer per zoom).
- Added an offline template-alias JSON editor (metadata only; not wired into the document parser).
- Added startup preflight and regression tests for session persistence, mismatch detection, template metadata, and PDF-copy annotation.
- Added error log for failures along the Waybill PDF export path.
- Retained the existing Stage-1-to-Stage-2 synchronization for Waybill mode; did not replace it with a new universal model.

## Known blockers
- Missing `rules.py` in the archived baseline.
- Missing PySide6 in this development environment: Windows GUI and complete exports not tested.
- Autosave uses original source-file paths, not embedded PDF bytes.
- Template alias editor does not change extraction logic or layout detection.
