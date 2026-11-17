# DocMatch v1.8.30.9 — Responsive Inspector & Field Select All

Base: v1.8.30.8 (MSC). Existing SWB presets and parsing engines preserved.

## Changes
- Inspector pane is rebalanced when the main window is resized, maximized or restored; existing splitter drag preference is retained where room allows.
- Inspector stage tabs have shorter labels, reducing horizontal clipping on smaller laptop screens. Full names remain available as tooltips.
- Findings tree now has an interactive parent checkbox for every Waybill field (e.g., Shipper). Clicking the parent toggles all **visible** child findings under the current category filter.
- Parent checkbox is unchecked/partially checked/checked according to its visible children. Individual finding toggles recalculate the parent state.
- Complete finding descriptions are available as tooltips when text is truncated.
- Added pure-Python regression tests for parent checkbox state and responsive splitter sizing.

## Notes
- Parent selection modifies which differences are selected for correction/export, not the source PDFs.
- When category filtering is active, the parent checkbox affects only findings displayed by that filter.
- GUI visual behavior must be verified on Windows with PySide6; Python syntax and available non-GUI regression tests passed in the build environment.
