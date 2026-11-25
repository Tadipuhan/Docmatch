# DocMatch v1.8.36.4 — Responsive PDF Workspace

## Perbaikan

- Memperbaiki layout Tab 1 dan Tab 2 yang melebar dan terpotong di sisi kanan setelah dokumen SI + PL dan SWB dimuat.
- Toolbar setiap PDF kini memakai dua baris: nama dokumen dan switch **Stabilo** di bagian atas, navigasi halaman dan zoom pada baris kedua. Dengan demikian nama dokumen tidak lagi menentukan lebar minimum panel PDF.
- Tombol pilih dokumen menggunakan kebijakan ukuran fleksibel sehingga nama file panjang tidak memaksa ukuran jendela melampaui layar. Nama/path lengkap tersedia melalui tooltip.
- Panel pemeriksaan mempunyai lebar minimum 260px dan lebar pilihan maksimal 430px pada pengaturan responsif. Lebar dua PDF dihitung dari ruang tersisa.
- Setelah unggah SI/PL atau SWB, splitter dijadwalkan menyesuaikan kembali ukuran panel.
- Mempertahankan mode SWB, Cross-Carrier, SI + PL, penanda merah/hijau, switch Sama ON/OFF, Tahap 1/2, Catatan Koreksi, serta ekspor portable ZIP/7z.

## Pengujian

- `python -m py_compile docmatch.py`
- `python -m pytest -q tests/test_responsive_workspace_18364.py tests/test_ui_layout_state.py`
- GUI PySide6 Windows tidak tersedia pada lingkungan build ini. Perlu smoke test pada monitor Windows 1366×768 / 1600×900, skala 100%/125%, sebelum dipakai produksi.
