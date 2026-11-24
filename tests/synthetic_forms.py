"""PDF formulir sintetis (rekonstruksi dari tangkapan layar; BUKAN dokumen asli).

Dipakai untuk menguji deteksi dan ekstraksi ketika sampel asli tidak dibundel.
PyMuPDF bila ada, jika tidak reportlab.
"""

W, H = 595, 842


def _px(fx, fy):
    return fx * W, fy * H


def meratus_waybill_ops(logo_as_text=False):
    """Meratus WAY BILL: logo GRAFIS (tanpa teks 'MERATUS'), caption di atas nilai.

    Posisi mengikuti MERATUS_SWB_CELLS (nilai) dan caption tepat di atasnya.
    """
    ops = []

    def text(fx, fy, s, size=6, bold=False):
        x, y = _px(fx, fy)
        ops.append(('text', x, y, s, size, bold))

    # logo vektor (kotak berwarna) - sengaja TANPA teks
    x, y = _px(.47, .060)
    ops.append(('rect', x, y, (70, 14)))
    if logo_as_text:
        text(.47, .075, 'MERATUS', 12, True)
    text(.65, .100, 'B/L No.', 5, True)
    text(.700, .120, 'JKT26104490', 7, True)
    text(.60, .144, 'WAY BILL', 13, True)
    # paragraf syarat di sisi kanan (bukan nilai field apa pun)
    para = ['Received by the carrier from the shipper in apparent good order and condition',
            'unless otherwise indicated herein the Goods or the container(s) or package(s)',
            'said to contain the cargo herein mentioned, to be carried subject to all',
            'In accepting this Bill of Lading, the Merchant agrees to be bound by all the',
            'stipulations, exceptions, terms and conditions on the face and back hereof',
            'In witness whereof the undersigned, on behalf of PT. Meratus Line the Master',
            'and the owner of the Vessels, has signed the number of Bill(s) of Lading']
    for i, s in enumerate(para):
        text(.52, .170 + i * .027, s, 4.5)
    # kolom kiri: caption (kecil, tebal) lalu nilai
    text(.053, .052, 'Shipper', 5, True)
    for i, s in enumerate(['PT. BRIDGESTONE TIRE INDONESIA', 'KAWASAN INDUSTRI SURYACIPTA,',
                           'JL. SURYA UTAMA KAV 8-13, KEL. KUTAMEKAR', 'KEC. CIAMPEL, KARAWANG',
                           'PROP. JAWA BARAT 41363']):
        text(.056, .072 + i * .011, s, 5)
    text(.053, .165, 'Consignee', 5, True)
    for i, s in enumerate(['BRIDGESTONE TYRES (P.N.G) PTY. LTD.', 'P.O. BOX 458 LAE']):
        text(.056, .185 + i * .011, s, 5)
    text(.053, .278, 'Notify Party', 5, True)
    for i, s in enumerate(['BRIDGESTONE TYRES (P.N.G) PTY. LTD.', 'P.O. BOX 458 LAE']):
        text(.056, .297 + i * .011, s, 5)
    # baris rute 1
    for fx, cap in ((.053, 'Pre-Carriage By'), (.237, 'Vessel'), (.406, 'Voy. No.'),
                    (.504, "Final Destination for The Merchant's reference only"),
                    (.727, 'Term'), (.801, 'Reference No.')):
        text(fx, .395, cap, 4.5, True)
    text(.240, .413, 'MERATUS KARIMUN', 5)
    text(.410, .413, 'GI058E', 5)
    text(.730, .413, 'CY/CY', 5)
    # baris rute 2
    for fx, cap in ((.053, 'Place of Receipt'), (.238, 'Port of Loading'), (.505, 'Port of Discharge'),
                    (.727, 'Delivery')):
        text(fx, .433, cap, 4.5, True)
    text(.056, .452, 'JAKARTA, INDONESIA', 5)
    text(.241, .452, 'JAKARTA, INDONESIA', 5)
    text(.508, .452, 'LAE, PAPUA NEW GUINEA', 5)
    text(.730, .452, 'LAE, PAPUA NEW GUINEA', 5)
    # muatan
    for fx, cap in ((.053, 'Container No. Seal No. Marks & Nos'), (.430, 'No. of Pkgs'), (.470, 'Kind of Pkgs'),
                    (.540, 'Description of Goods'), (.700, 'Gross Weight'), (.865, 'Measurement')):
        text(fx, .527, cap, 4.5, True)
    text(.056, .545, 'MRTU9647507/J344673/40 HC', 5)
    text(.430, .545, '549', 5)
    text(.470, .545, 'PIECE', 5)
    for i, s in enumerate(['BRIDGESTONE BRAND NEW TIRES', 'INVOICE NO : 26B93PG1']):
        text(.436, .560 + i * .011, s, 5)
    text(.703, .547, '11,092.239 KGS', 5)
    text(.868, .547, '73.841 CBM', 5)
    # bawah
    text(.350, .735, 'OCEAN FREIGHT AND CHARGES', 5, True)
    text(.350, .745, 'Rates, Weight and/or Measurement subject to correction', 4)
    text(.053, .805, 'Payable at', 4.5, True)
    text(.056, .825, 'JAKARTA', 5)
    text(.296, .805, 'No. of Original Bill (s) of Lading', 4.5, True)
    text(.299, .825, '1(ONE)', 5)
    text(.600, .805, 'As Agent for the Carrier', 4.5, True)
    text(.053, .840, 'Shipped on Board the Vessel', 4.5, True)
    text(.056, .860, '03/10/2026', 5)
    text(.326, .840, 'Place and Date of Issued', 4.5, True)
    text(.329, .860, 'JAKARTA / 03/10/2026', 5)
    return ops


def render(path, ops):
    try:
        import pymupdf as fitz
        doc = fitz.open()
        page = doc.new_page(width=W, height=H)
        for op in ops:
            if op[0] == 'rect':
                _, x, y, (w, h) = op
                page.draw_rect(fitz.Rect(x, y, x + w, y + h), fill=(0.1, 0.3, 0.7))
            else:
                _, x, y, s, size, bold = op
                page.insert_text((x, y), s, fontsize=size, fontname='hebo' if bold else 'helv')
        doc.save(str(path))
        doc.close()
        return
    except (ImportError, AttributeError, TypeError):
        pass
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=(W, H))
    for op in ops:
        if op[0] == 'rect':
            _, x, y, (w, h) = op
            c.setFillColorRGB(0.1, 0.3, 0.7)
            c.rect(x, H - y - h, w, h, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)
        else:
            _, x, y, s, size, bold = op
            c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
            c.drawString(x, H - y, s)
    c.save()


def make_meratus_waybill(path, logo_as_text=False, replace=None):
    ops = meratus_waybill_ops(logo_as_text)
    if replace:
        ops = [op if op[0] == 'rect' else (op[0], op[1], op[2], replace.get(op[3], op[3]), op[4], op[5])
               for op in ops]
    render(path, ops)
