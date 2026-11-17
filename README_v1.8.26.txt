DocMatch v1.8.26 — Dynamic Findings Filter / Simple OCR / Linked Selection / Parameter Search

Changes versus v1.8.25
1) Daftar Ketidaksesuaian only offers categories actually present in the current findings. Possible kinds: Perubahan, Hilang, Berlebih, Perlu Verifikasi, or any other actual kind. No category is shown if absent. 'Semua' remains always available.
2) Inspector has one OCR recovery button: 'Perbaiki Pembacaan Otomatis'. Old separate OCR A/B controls and lengthy candidate dumps are hidden. Background OCR still handles both A and B with fallback. An OCR candidate is previewed in editable text only if an old value is empty/damaged, candidate score >=65, and the text has no obvious unrelated clauses keywords. Nothing is committed to Stage 1 without confirmation. Recovery is not a guaranteed fix for unrecognizable text.
3) Drawing a region on either PDF will automatically request a candidate for the corresponding field in the other PDF; manually drawn coordinates are preserved and not replaced by asynchronous suggestions. Candidate is not confirmed automatically.
4) Daftar Parameter includes a search text field and checkboxes. Right-click directly on either PDF opens a searchable checkbox parameter menu. A checked row selected there navigates to that parameter.
5) Page 1 GSL layout presets and the original Stage 1 comparison remain unchanged.

Cautions
- Source archive still lacks rules.py, inherited from supplied v1.8.19. Restore rules.py from the working DocMatch installation.
- Requires PySide6, PyMuPDF, and offline Tesseract for OCR. Runtime Windows GUI test has NOT been performed here.
- 'Perbaiki Pembacaan' does NOT guarantee OCR correctness; inspect both PDF crops and confirm any changes.
- The sidebar checkbox is a navigation/selection helper, not a command to delete findings.
- On switching a parameter while OCR is still running, stale results are ignored by generation token.
