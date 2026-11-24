"""Offline reference-side field extraction independent of the chosen SWB template.

Only explicit labelled values are accepted; do not infer a field from a similar-looking
unlabelled value. The examined document continues using its carrier-specific extractor.
"""
from __future__ import annotations
import re
import unicodedata
import pymupdf as fitz


def norm_label(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold().replace('&', 'and')
    return re.sub(r'[^a-z0-9]+', '', text)


# Carrier-independent equivalents. Ambiguous names are intentionally not mapped
# (e.g. Port of Discharge is never automatically Final Destination).
ALIASES = {
    'Waybill Number': ('Sea Waybill No.', 'Sea Waybill Number', 'Bill of Lading No.',
                       'Bill of Lading Number', 'B/L No.', 'B/L Number', 'BL No.',
                       'Document Number', 'SWB No.', 'Waybill No.'),
    'Document Number': ('Waybill Number', 'B/L No.', 'Sea Waybill No.', 'BL Number'),
    'Booking Number': ('Booking No.', 'Booking Reference', 'Booking Ref.', 'Booking ID'),
    'Booking Reference': ('Booking Number', 'Booking No.', 'Booking Ref.'),
    'Shipper': ('Shipper/Exporter', 'Exporter', 'Shipper Name and Address'),
    'Consignee': ('Consignee Name and Address',),
    'Notify Party': ('Notify', 'Notify Name and Address', 'Notify Parties'),
    'Vessel': ('Vessel Name', 'Ocean Vessel'),
    'Voyage Number': ('Voyage No.', 'Voy No.', 'Voyage'),
    'Vessel / Voyage': ('Vessel and Voyage', 'Vessel Voyage', 'Vessel and Voyage No.'),
    'Port of Loading': ('POL', 'Loading Port'),
    'Port of Discharge': ('POD', 'Discharge Port'),
    'Place of Receipt': ('Receipt Place',),
    'Place of Delivery': ('Delivery Place',),
    'Final Place of Delivery': ('Final Delivery Place',),
    'Final Destination': ('Final Destination Port',),
    'Pre-Carriage': ('Pre Carriage By', 'Pre-Carriage By', 'Pre Carriage'),
    'Initial Carriage': ('Pre-Carriage By',),
    'Place & Date of Issue': ('Place and Date of Issue', 'Issue Place and Date', 'Place & Date of Issued'),
    'Port of Destination': ('Destination Port',),
    'Point and Country of Origin': ('Country of Origin', 'Point and Country of Origin'),
    'Container & Seal': ('Container and Seal', 'Container No. / Seal No.', 'Container Numbers / Seal Numbers'),
    'Main - Container & Seal': ('Container & Seal', 'Container No. / Seal No.', 'Container and Seal'),
    'Cargo Description': ('Description of Goods', 'Goods Description', 'Description of Cargo'),
    'Main - Cargo Description': ('Cargo Description', 'Description of Goods'),
    'Main - Clauses': ('Clauses', 'Main Clauses'),
    'Attached List - Clauses': ('Attached Clauses', 'Attached List Clauses'),
    'Attached List - Description of Goods': ('Attached Goods Description', 'Attached List Cargo Description'),
    'Attached List - MKS & NOS/SEAL.NO': ('Marks and Numbers / Seal No.', 'Attached Marks and Seal'),
    'Quantity': ('Number of Packages', 'Total Quantity', 'Pieces'),
    'Gross Weight': ('Total Gross Weight', 'Cargo Gross Weight'),
    'Gross Measurement': ('Total Gross Measurement', 'Measurement Total', 'Total Measurement'),
    'Weight & Measurement': ('Weight and Measurement',),
    'Freight Payable At': ('Freight & Charges Payable At',),
    'Freight To Be Paid At': ('Freight Payable At',),
    'Service Contract Number': ('Service Contract No.', 'Svc Contract'),
    'Export References': ('Export Reference',),
    'Forwarding Agent': ('Forwarding Agent Reference',),
    'Further Routing': ('Additional Routing',),
    'Type of Movement': ('Movement Type',),
    'No & Kind of Packages': ('Number and Kind of Packages',),
    'Number of Original Waybills': ('Number of Original B/L', 'Number of Originals'),
    'Freight & Charges': ('Freight Charges',),
    'Freight Prepayable At': ('Freight Prepaid At',),
}


def _aliases(field):
    return {norm_label(v) for v in (field, *ALIASES.get(field, ())) if v}


def _lines(page, page_no):
    result = []
    for block in page.get_text('dict', sort=True)['blocks']:
        for line in block.get('lines', []):
            spans = [s for s in line.get('spans', []) if s.get('text', '').strip()]
            if spans:
                result.append({'text': ''.join(s['text'] for s in spans).strip(),
                               'rect': fitz.Rect(line['bbox']), 'page': page_no})
    return sorted(result, key=lambda l:(round(l['rect'].y0,1), l['rect'].x0))


def _possible_labels(lines, targets):
    """Label lines plus optional wrapped labels; no fuzzy matching of arbitrary text."""
    found = []
    claimed = set()
    for i, line in enumerate(lines):
        cleaned = norm_label(line['text'].rstrip(':'))
        next_cleaned = ''
        if i+1 < len(lines):
            nxt = lines[i+1]
            if abs(nxt['rect'].x0 - line['rect'].x0) < 5 and 5 < nxt['rect'].y0 - line['rect'].y0 < 19:
                next_cleaned = norm_label(line['text'] + ' ' + nxt['text'])
        for field, aliases in targets.items():
            if field in claimed: continue
            if cleaned in aliases or next_cleaned in aliases:
                found.append((i, line, field))
                claimed.add(field)
                break
            # A single text line may contain "Port of Loading: JAKARTA".
            # Only accept an explicit separator, never a substring of prose.
            match = re.match(r'^\s*([^:：]{2,75})\s*[:：]\s*(.+?)\s*$',line['text'])
            if match and norm_label(match.group(1)) in aliases:
                inline = dict(line, inline_value=match.group(2).strip())
                found.append((i,inline,field))
                claimed.add(field)
                break
    return sorted(found, key=lambda v: v[1]['rect'].y0)


# Frasa cetak khas formulir Meratus (dinormalisasi: huruf kecil, hanya a-z0-9). Surat rujukan
# tidak memuat frasa-frasa ini; formulirnya selalu memuatnya walaupun logonya berupa gambar.
_MERATUS_PRINTED_CUES = (
    'oceanfreightandcharges', 'asagentforthecarrier', 'shippedonboardthevessel',
    'placeanddateofissue', 'nooforiginalbill', 'finaldestinationforthemerchant',
    'containernosealnomarks', 'particularsfurnishedbythemerchant',
)


def _looks_like_meratus_form(lines, page):
    """Way Bill / Bill of Lading Meratus dikenali dari STRUKTUR cetak, bukan hanya kata 'meratus'.

    Pada Way Bill, 'MERATUS' adalah logo grafis sehingga tidak ada teks 'meratus' di header;
    tanpa aturan ini dokumen itu dikira surat rujukan dan nilai field dibaca dari label
    terdekat (paragraf syarat terbaca sebagai Consignee/Notify Party).
    Syarat: judul WAY BILL / BILL OF LADING di bagian atas, heading 'Shipper' di kiri atas
    (geometri yang sama dengan waybill_rules.meratus_layout), dan >= 3 frasa cetak khas formulir.
    """
    top = [norm_label(l['text']) for l in lines if l['rect'].y0 < page.rect.height * .20]
    if not any('waybill' in t or 'billoflading' in t for t in top):
        return False
    heading = any(norm_label(l['text']) == 'shipper' and l['rect'].x0 < page.rect.width * .20
                  and .005 < l['rect'].y0 / page.rect.height < .10 for l in lines)
    if not heading:
        return False
    full = norm_label(' '.join(l['text'] for l in lines))
    return sum(cue in full for cue in _MERATUS_PRINTED_CUES) >= 3


def _is_carrier_form(lines, page):
    """Official carrier forms should continue through their precise profile."""
    header = ' '.join(l['text'].casefold() for l in lines if l['rect'].y0 < page.rect.height*.17)
    # These are strong form-specific tokens, not generic descriptions in a letter.
    strong = ('mediterranean shipping company s.a.', 'goldstar line',
              'sea waybill of lading for port', 'particulars furnished by shipper',
              'ocean network express pte.', 'bill of lading for ocean transport',
              'bill of lading for ocean transport or multimodal transport')
    if any(token in header for token in strong): return True
    if ('meratus' in header and ('bill of lading' in header or 'way bill' in header)): return True
    if _looks_like_meratus_form(lines, page): return True
    if ('scac' in header and 'maeu' in header): return True
    if ('shipper/exporter' in header and 'booking no.' in header
            and ('sea waybill' in header or 'bill of lading' in header)):
        return True
    # ANL / CNC / CMA CGM have a distinct, multi-column waybill layout. The
    # previous detector omitted them, so PDF B could be sent to the generic
    # reference-label reader instead of its calibrated carrier extractor.
    # Require multiple *form* clues; an ordinary letter mentioning ANL alone
    # must not be classified as a carrier document.
    full = ' '.join(line['text'].casefold() for line in lines)
    title = ('draft waybill' in full or 'non negotiable' in full or
             'non-negotiable' in full or 'sea waybill no.' in full or
             'bill of lading no.' in full)
    carrier = ('anl singapore' in full or 'anl shipping' in full or
               'cma cgm' in full or 'cnc line' in full or
               re.search(r'\bcarrier\s*:\s*anl\b', full) is not None)
    form_labels = sum(token in full for token in (
        'port of loading', 'port of discharge', 'marks and seals',
        'marks and numbers', 'number of original waybills',
        'shipper', 'consignee', 'notify party', 'voyage number'))
    if title and carrier and form_labels >= 4:
        return True
    # Alternative when ANL logo is rendered as vectors/image instead of text:
    # a rare combination of waybill title and distinctive ANL form sections.
    distinctive = sum(token in full for token in (
        'number of original waybills', 'freight to be paid at',
        'no and kind of packages', 'final place of delivery',
        'draft waybill', 'non negotiable'))
    if title and form_labels >= 6 and distinctive >= 3:
        return True
    return False


def detect_flexible_pdf(path, fields=None):
    """Decide whether PDF A is a labelled reference rather than an SWB carrier form.

    A single labelled field is enough if the PDF has an explicit data-table heading;
    otherwise at least two unrelated recognised labels are required.
    """
    with fitz.open(path) as doc:
        if not len(doc): return False
        first = doc[0]
        lines = _lines(first, 0)
        if _is_carrier_form(lines, first): return False
        header = ' '.join(l['text'].casefold() for l in lines[:90])
        labelled = ('field / parameter' in header or 'nilai dokumen' in header or
                    'parameter / value' in header or 'field name' in header)
        if fields is None:
            from waybill_rules import GSL_CELLS, FIELDS, ONE_CELLS, MAERSK_CELLS, MERATUS_CELLS, MSC_CELLS
            names = set(GSL_CELLS)|{n for n,_ in FIELDS}|set(ONE_CELLS)|set(MAERSK_CELLS)|set(MERATUS_CELLS)|set(MSC_CELLS)
        else:
            names = set(fields)
        found = {field for _, _, field in _possible_labels(lines,{f:_aliases(f) for f in names})}
        is_letter=any(word in header for word in ('surat', 'memo', 'konfirmasi', 'confirmation', 'invoice', 'instruction', 'rujukan', 'reference data'))
        if len(found)>=2 or (found and (labelled or is_letter)): return True
        # Field labels can span different pages in a reference letter.
        if len(doc)>1:
            for pno in range(1, min(3,len(doc))):
                found.update(f for _,_,f in _possible_labels(_lines(doc[pno],pno),{f:_aliases(f) for f in names}))
                if len(found)>=2: return True
        return False


def _value_from_label(lines, labels, index, label, page, tall=False):
    """Read a value to the right or below the label, constrained by next label.

    Keep the original PDF coordinates to support side-specific highlighting.

    tall=True (profil ANL): nilai boleh melebihi 65/95 pt selama baris-barisnya berurutan
    rapat; berhenti pada label berikutnya atau jeda antar-baris yang jelas lebih besar dari
    jarak baris. Tanpa ini, sel tabel berisi alamat/deskripsi panjang terpotong.
    """
    r = label['rect']
    if label.get('inline_value'):
        value=label['inline_value']
        # Locate only the value text in the source PDF, not the label.
        matches=page.search_for(value)
        matching=[box for box in matches if abs(box.y0-r.y0)<max(8,r.height)]
        rect=matching[0] if matching else r
        return [{'text':value,'rect':rect,'page':label['page']}]
    nearby = [line for line in lines if line is not label and
              line['rect'].x0 >= r.x1 + 7 and
              abs(line['rect'].y0-r.y0) < max(8, r.height*.85)]
    next_rows = [other['rect'].y0 for _,other,_ in labels if other['rect'].y0>r.y0+3]
    next_y = min(next_rows, default=page.rect.height*.95)
    if nearby:
        value_x = min(line['rect'].x0 for line in nearby)
        # Horizontal two-column row, but do not absorb labels on right.
        y_stop = min(next_y, r.y0+(240 if tall else 65))
        rows = [line for line in lines if line['rect'].x0 >= value_x-4 and
                r.y0-4 <= line['rect'].y0 < y_stop-2 and line is not label]
    else:
        # Single column: value starts just below the field label.
        y_stop = min(next_y, r.y0+(240 if tall else 95))
        rows = [line for line in lines if r.y1+1 < line['rect'].y0 < y_stop-2 and line is not label]
    rows.sort(key=lambda line:(round(line['rect'].y0,1),line['rect'].x0))
    if tall and rows:
        kept=[rows[0]]
        for row in rows[1:]:
            prev=kept[-1]['rect']
            if row['rect'].y0-prev.y1 > 1.6*prev.height+4:   # jeda besar: nilai sudah berakhir
                break
            kept.append(row)
        rows=kept
    return rows


def _word_boxes(page, rows, page_no):
    """Kata individual (teks + kotak) di dalam baris-baris nilai; cadangan: kotak baris."""
    all_words = page.get_text('words', sort=True)
    out = []
    for line in rows:
        box = fitz.Rect(line['rect'])
        box = fitz.Rect(box.x0 - .6, box.y0 - .6, box.x1 + .6, box.y1 + .6)
        inside = [w for w in all_words if str(w[4]).strip() and
                  box.contains((fitz.Rect(w[:4]).tl + fitz.Rect(w[:4]).br) * .5)]
        inside.sort(key=lambda w: w[0])
        if inside:
            out.extend({'word': str(w[4]).strip(), 'rect': fitz.Rect(w[:4]), 'page': page_no} for w in inside)
        else:
            out.append({'word': line['text'], 'rect': line['rect'], 'page': page_no})
    return out


def extract_flexible(path, fields, word_level=False):
    """Extract explicit labelled fields from arbitrary text-bearing reference PDFs.

    Unknown or ambiguously missing fields remain invalid, never fabricated.

    word_level=True (hanya dipakai profil ANL): 'words' berisi KATA individual dari nilai,
    bukan satu kotak per baris, sehingga penanda mengikuti teks nilai secara presisi.
    """
    targets={f:_aliases(f) for f in fields}
    result={f:{'text':'','words':[],'valid':False,'source':'Flexible labels',
               'reason':'Label/nilai field tidak dapat ditemukan pada dokumen rujukan'} for f in fields}
    with fitz.open(path) as doc:
        for pno, page in enumerate(doc):
            lines = _lines(page,pno)
            labels = _possible_labels(lines,targets)
            for idx,label,field in labels:
                if result[field]['valid']: continue
                rows = _value_from_label(lines,labels,idx,label,page,tall=word_level)
                if not rows: continue
                value = ' '.join(line['text'] for line in rows).strip()
                if not value: continue
                result[field]={'text':value,
                               'words':(_word_boxes(page,rows,pno) if word_level else
                                        [{'word':line['text'],'rect':line['rect'],'page':pno} for line in rows]),
                               'valid':True,'source':'Flexible labels'}
    return result
