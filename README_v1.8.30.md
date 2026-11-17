# DocMatch v1.8.30 — Consolidated Foundation (development)

**Baseline:** v1.8.29. This single package combines incremental work toward the five requested milestones (1.8.30–1.8.34). It is **not** a certified production release.

## Changes

- **Stability / Export:** previous safe-export logic retained, exception logging to `~/docmatch_errors.log`, `preflight.py` for checking mandatory files and imports, regression tests covering portable data workflows and PDF-copy annotations. Existing `rules.py` dependency remains external to the source ZIP.
- **Unified Validation State:** original in-memory Stage-1 baseline plus Stage-2 verified records remain the source of active findings; session snapshots now save both stages, annotation flags, marks and audit events. This is an incremental consolidation, **not** a complete reactive single-store architecture.
- **Session Recovery & Audit:** Save Session / Open Session buttons, atomic JSON snapshots `.dmjson`, delayed autosave, document SHA-256 verification on load, audit log on field confirmation/checklist changes. Session may refer to original documents at their original paths. Files are not embedded.
- **PDF Viewer / Annotation:** up to 3 clean HiDPI page renders cached per viewer, with overlay highlighting rendered separately. Existing synchronized rectangles and multi-parameter annotation preserved.
- **Template Manager / Performance:** editable offline JSON aliases via Template / Alias button; current coordinate detection rules intentionally unchanged. Cache reduces re-renders, but OCR batching and template-driven geometry are not redesigned.

## How to use

1. Restore missing `rules.py` from a trusted working DocMatch project. Keep the bundled Python modules in the same folder.
2. Install dependencies in an isolated environment (see `requirements-build.txt`) and run `py preflight.py`.
3. Run `py docmatch.py`, select documents, run comparison; click **Simpan Sesi** to save or **Buka Sesi** to restore a previously saved `.dmjson` file. Autosave is written to `~/Documents/DocMatch/autosave.dmjson` after edits / on close.
4. Use **Template / Alias** to edit parameter name metadata. This does **not** change extraction coordinates or search aliases used by the current locator, yet.
5. Export PDF/JSON/DOCX through existing Hasil & Ekspor controls.

## Tests

`python -m pytest -q tests` — uses a generated PDF test fixture, no user documents.

## Known limits / incomplete work

- GUI startup and end-to-end export cannot be validated here because PySide6 and `rules.py` are unavailable in the build environment. **Test on Windows** before rollout.
- General-document comparison has not been migrated to a unified field-based model; Stage-2 promotion remains principally supported in Waybill mode.
- Undo/redo actions and external crash-recovery prompts are not implemented; `.dmjson` files can be opened using **Buka Sesi**.
- `template_aliases.json` is metadata only; not applied to OCR or rectangle detection.
- Existing GSL OCR/field geometry has not been altered.
- Atomic session saves require file paths to remain accessible. Restoring a moved/modified PDF will be blocked to prevent misplaced rectangles.
