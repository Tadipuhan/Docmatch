DocMatch v1.8.10 — GSL page-one field corrections
- Booking Number and Waybill Number: reduce caption mask to avoid dropping short numeric data; label lines still filtered.
- GSL page 1: one field-level difference per changed physical cell, not multiple OCR word fragments.
- Correction note: full reference text only; remove automatic change explanations, including previously saved group notes.
- Attached List processing unchanged.
Caution: OCR must still be validated on original GSL PDFs. Rebuild Windows portable EXE using build_portable.bat.
