"""Offline Shipping Instruction + Packing List reference extraction for DocMatch.

Source authority: SI supplies people, booking, ports, vessel and cargo values;
PL supplies container, seal, invoice and PL date.  A temporary SI+PL PDF
provides real page coordinates for annotations.  Neither source is altered.
No OCR, filename-based guessing, or cross-column fallback is performed.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import pymupdf as fitz


class ReferenceReadError(ValueError):
    pass


@dataclass
class SourceInfo:
    source: str
    text: str
    page: int


def verify_pdf(path: str | Path, kind: str) -> None:
    path = Path(path)
    if path.suffix.lower() != '.pdf':
        raise ReferenceReadError(f'{kind} harus berupa file PDF (.pdf).')
    if not path.is_file():
        raise ReferenceReadError(f'File {kind} tidak ditemukan: {path}')
    try:
        with fitz.open(path) as doc:
            if not len(doc):
                raise ReferenceReadError(f'File {kind} tidak memiliki halaman.')
            if not any(page.get_text().strip() for page in doc):
                raise ReferenceReadError(
                    f'{kind} tidak memiliki lapisan teks. PDF scan memerlukan OCR atau verifikasi manual.')
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise ReferenceReadError(f'File {kind} tidak valid: {exc}') from exc


def merge_pdf(si_path: str | Path, pl_path: str | Path, target: str | Path) -> int:
    """Compose reference viewer: SI pages first, PL pages second. Return PL page offset."""
    verify_pdf(si_path, 'Shipping Instruction (SI)')
    verify_pdf(pl_path, 'Packing List (PL)')
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(si_path) as si, fitz.open(pl_path) as pl, fitz.open() as merged:
        merged.insert_pdf(si)
        offset = len(si)
        merged.insert_pdf(pl)
        merged.set_metadata({'title': 'DocMatch Reference: Shipping Instruction + Packing List',
                             'subject': 'Temporary viewing copy; source PDFs unchanged'})
        merged.save(target, garbage=3, deflate=True)
    return offset


def _words(page, page_offset=0):
    return [{'word': str(w[4]), 'rect': fitz.Rect(w[:4]), 'page': page_offset}
            for w in page.get_text('words', sort=True) if str(w[4]).strip()]


def _line_groups(words):
    lines = []
    for item in sorted(words, key=lambda w: (w['rect'].y0, w['rect'].x0)):
        r = item['rect']; cy = (r.y0 + r.y1) * .5
        match = next((g for g in reversed(lines[-8:]) if abs(g['cy'] - cy) < 2.8), None)
        if match is None:
            lines.append({'cy':cy, 'words':[item]})
        else:
            match['words'].append(item)
    for row in lines:
        row['words'].sort(key=lambda w: w['rect'].x0)
    return sorted(lines, key=lambda g:g['cy'])


def _label(words, pattern, *, left=None, right=None, first=True):
    regex = re.compile(pattern, re.I)
    eligible = [row for row in _line_groups(words)
                if (left is None or any(w['rect'].x0 < left for w in row['words']))
                and (right is None or any(w['rect'].x0 >= right for w in row['words']))
                and regex.search(' '.join(w['word'] for w in row['words']))]
    if not eligible:
        return None
    return eligible[0]['cy'] if first else eligible[-1]['cy']


def _box(words, x0, y0, x1, y1):
    return [w for w in words if x0 <= (w['rect'].x0+w['rect'].x1)*.5 <= x1
            and y0 <= (w['rect'].y0+w['rect'].y1)*.5 <= y1]


def _record(words, *, source, required=False):
    if not words:
        return {'text':'', 'words':[], 'valid':False, 'source':source,
                'reason':'Nilai tidak terdeteksi pada area field sumber'}
    lines = _line_groups(words)
    text = '\n'.join(' '.join(w['word'] for w in row['words']) for row in lines).strip()
    return {'text':text, 'words':words, 'valid':bool(text), 'source':source}


def _value_on_row(words, anchor_y, x0, x1, *, source, y_tolerance=7):
    if anchor_y is None:
        return _record([], source=source)
    return _record(_box(words,x0,anchor_y-y_tolerance,x1,anchor_y+y_tolerance),source=source)


def _extend_y(value, fallback, limit):
    return min(limit, value if value is not None else fallback)


def _extract_si(page):
    w=_words(page)
    W=page.rect.width
    left_val=.183*W; left_end=.485*W
    right_val=.595*W; right_end=.99*W
    # Anchors are found from printed labels, not a hardcoded SI filename.
    consignee_y=_label(w,r'\bConsignee\s*:',left=.65*W)
    shipper_y=_label(w,r'\bShipper\b',left=.20*W)
    notify_y=_label(w,r'\bNotify\s+Party\b',right=.50*W)
    loading_y=_label(w,r'\bPort\s+of\s+Loading\b',left=.20*W)
    dest_y=_label(w,r'\bPort\s+of\s+Destination\b',left=.20*W)
    carrier_y=_label(w,r'\b1st\s+Carrier\b',right=.50*W)
    booking_y=_label(w,r'\bBOOKING\s+NO\b',left=.20*W)
    qty_header_y=_label(w,r'Description\s+of\s+Goods\s+and\s+Quantity')
    net_y=_label(w,r'\bNet\s+Weight\b',left=.20*W)
    gross_y=_label(w,r'\bGross\s+Weight\b',left=.20*W)
    meas_y=_label(w,r'\bMeasurements?\b',left=.20*W)
    hs_y=_label(w,r'\bHS\s+CODE\b')
    invoice_line_y=_label(w,r'\bINVOICE\s+NO\.?\b',first=True)
    out={}
    out['Booking Number']=_value_on_row(w,booking_y,left_val,left_end,source='SI',y_tolerance=5)
    out['Shipper']=_record(_box(w,left_val,(shipper_y or 0)-7,left_end,
                                    _extend_y(loading_y,page.rect.height*.36,page.rect.height)-8),source='SI')
    out['Consignee']=_record(_box(w,right_val,(consignee_y or 0)-7,right_end,
                                     _extend_y(notify_y,page.rect.height*.22,page.rect.height)-8),source='SI')
    out['Notify Party']=_record(_box(w,right_val,(notify_y or 0)-7,right_end,
                                       _extend_y(carrier_y,page.rect.height*.36,page.rect.height)-10),source='SI')
    out['Port of Loading']=_value_on_row(w,loading_y,left_val,left_end,source='SI')
    out['Port of Discharge']=_value_on_row(w,dest_y,left_val,left_end,source='SI')
    out['Vessel / Voyage']=_value_on_row(w,carrier_y,right_val,right_end,source='SI')
    if out['Vessel / Voyage']['valid']:
        from cross_carrier import split_compound_record
        out['Vessel']=split_compound_record(out['Vessel / Voyage'],'Vessel')
        out['Voyage Number']=split_compound_record(out['Vessel / Voyage'],'Voyage Number')
    # Description has a distinct, centered block immediately preceding weight
    # rows. Do not absorb the PL item table or unrelated SI form fields.
    cargo_start=(qty_header_y or page.rect.height*.51)+13
    cargo_stop=(net_y or page.rect.height*.61)-7
    cargo=_box(w,.28*W,cargo_start,.75*W,cargo_stop)
    out['Cargo Description']=_record(cargo,source='SI')
    if qty_header_y is not None:
        first_row = [g for g in _line_groups(_box(w,.30*W,cargo_start,.67*W,cargo_stop))
                     if re.search(r'\bPIECES?\b', ' '.join(ww['word'] for ww in g['words']),re.I)]
        # The first line below heading states total quantity; the second may be
        # the same number in tyre units and is not counted twice.
        out['Quantity']=_record(first_row[0]['words'],source='SI') if first_row else _record([],source='SI')
    else:
        out['Quantity']=_record([],source='SI')
    out['Net Weight']=_value_on_row(w,net_y,.24*W,.49*W,source='SI')
    out['Gross Weight']=_value_on_row(w,gross_y,.24*W,.49*W,source='SI')
    out['Gross Measurement']=_value_on_row(w,meas_y,.24*W,.49*W,source='SI')
    out['HS Code']=_value_on_row(w,hs_y,.445*W,.73*W,source='SI')
    # Cargo description contains the source invoice (PL is independently checked).
    if invoice_line_y is not None and qty_header_y is not None and invoice_line_y > qty_header_y:
        out['SI Invoice Number']=_value_on_row(w,invoice_line_y,.48*W,.74*W,source='SI')
    else:
        out['SI Invoice Number']=_record([],source='SI')
    return out


def _extract_pl(page, offset):
    w=_words(page,offset); W=page.rect.width
    right_val=.78*W; right_end=.99*W
    labels={'PL Date':r'\bDate\s*:', 'Invoice Number':r'\bInvoice\s+No\.?\s*:',
            'Container No.':r'\bContainer\s+No\.?\s*:', 'Seal No.':r'\bSeal\s+No\.?\s*:'}
    result={}
    for name, label in labels.items():
        anchor=_label(w,label,right=.60*W)
        result[name]=_value_on_row(w,anchor,right_val,right_end,source='PL',y_tolerance=5.5)
    # Pair is built from the separately selected PDF words; the label characters
    # and adjacent company address cannot leak into the comparison value.
    container=result['Container No.']; seal=result['Seal No.']
    if container['valid'] and seal['valid']:
        result['Container & Seal']={
            'text':container['text'].strip()+' / '+seal['text'].strip(),
            'words':container['words']+seal['words'], 'valid':True,'source':'PL'}
    else:
        result['Container & Seal']=_record([],source='PL')
    return result


def extract_pl_si(si_path: str | Path, pl_path: str | Path):
    """Return (reference records, metadata), with SI+PL virtual page numbers."""
    verify_pdf(si_path,'Shipping Instruction (SI)')
    verify_pdf(pl_path,'Packing List (PL)')
    with fitz.open(si_path) as si, fitz.open(pl_path) as pl:
        si_records=_extract_si(si[0])
        pl_records=_extract_pl(pl[0],len(si))
        # The user-specified source-of-truth hierarchy is intentional.
        combined=dict(si_records)
        combined.update({key:pl_records[key] for key in
                         ('Container & Seal','Invoice Number','PL Date','Container No.','Seal No.')})
        if 'Weight & Measurement' not in combined and combined['Gross Weight']['valid'] and combined['Gross Measurement']['valid']:
            combined['Weight & Measurement']={
                'text':combined['Gross Weight']['text']+' / '+combined['Gross Measurement']['text'],
                'words':combined['Gross Weight']['words']+combined['Gross Measurement']['words'],
                'valid':True, 'source':'SI'}
        meta={'si':str(si_path),'pl':str(pl_path),
              'pl_date':pl_records['PL Date']['text'],
              'invoice_pl':pl_records['Invoice Number']['text'],
              'invoice_si':si_records['SI Invoice Number']['text'],
              'container':pl_records['Container No.']['text'],
              'seal':pl_records['Seal No.']['text']}
        # An invoice disagreement between reference files needs intervention.
        inv_a=meta['invoice_pl'].replace(' ','').upper()
        inv_b=meta['invoice_si'].replace(' ','').upper()
        meta['conflicting_invoice']=bool(inv_a and inv_b and inv_a != inv_b)
        # Require identity anchors, not just any PDF text. Incomplete fields can
        # be flagged for review individually instead of falsely matching.
        if sum(combined[k]['valid'] for k in ('Booking Number','Shipper','Consignee','Notify Party')) < 2:
            raise ReferenceReadError('SI tidak sesuai struktur yang dikenali: field identitas terlalu sedikit.')
        if sum(combined[k]['valid'] for k in ('Invoice Number','Container & Seal')) < 1:
            raise ReferenceReadError('PL tidak sesuai struktur yang dikenali: invoice/container tidak ditemukan.')
        return combined,meta


def _num(text):
    m=re.search(r'(?<!\d)(\d[\d,]*(?:\.\d+)?)',text)
    return m.group(1).replace(',','') if m else None


def equivalent(field: str, a: str, b: str):
    """Safe semantic equivalence; None means not enough evidence to conclude."""
    from cross_carrier import container_pairs, measurement_signature, normalized_value
    fld=field.casefold().removeprefix('main - ')
    if fld in ('shipper','consignee','notify party'):
        # Ignore layout wraps/case but preserve actual punctuation changes.
        # e.g. SI `CIAMPEL,` versus SWB `CIAMPEL.` is a real correction.
        return re.sub(r'\s+', '', a).casefold() == re.sub(r'\s+', '', b).casefold()
    if fld in ('container & seal','main - container & seal'):
        left,right=container_pairs(a),container_pairs(b)
        return left==right if left is not None and right is not None else None
    if fld in ('quantity','total qty','total quantity'):
        na,nb=_num(a),_num(b)
        if not na or not nb:return None
        if float(na)!=float(nb):return False
        unit_pattern=r'\b(PIECES?|PCS|PACKAGES?|PKGS?|CARTONS?|CTNS?|CONTAINERS?|TYRES?|TIRES?)\b'
        ua=re.search(unit_pattern,a,re.I);ub=re.search(unit_pattern,b,re.I)
        canonical={'pcs':'piece','pieces':'piece','piece':'piece',
                   'packages':'package','package':'package','pkgs':'package','pkg':'package',
                   'cartons':'carton','carton':'carton','ctns':'carton','ctn':'carton',
                   'containers':'container','container':'container',
                   'tyres':'tyre','tyre':'tyre','tires':'tyre','tire':'tyre'}
        if ua and ub:
            return canonical.get(ua.group(1).lower())==canonical.get(ub.group(1).lower())
        return None  # unknown quantity unit; request manual verification
    if fld in ('gross weight','gross measurement','weight & measurement'):
        # Accept 65.6100 M3 and 65.610 CBM as the same amount. A missing unit
        # is unknown, not a silently accepted match.
        sa=measurement_signature(a,field);sb=measurement_signature(b,field)
        if sa is None or sb is None:return None
        def standard_unit(unit):
            unit=re.sub(r'[^a-z0-9]','',unit.casefold())
            if unit in {'kg','kgs','kilogram','kilograms'}:return 'kg'
            if unit in {'m3','cbm','cum','cubicmeter','cubicmeters'}:return 'm3'
            if unit in {'ton','tons','tonne','tonnes'}:return 'tonne'
            return unit
        return (tuple((kind,round(float(q),6),standard_unit(unit)) for kind,q,unit in sa)==
                tuple((kind,round(float(q),6),standard_unit(unit)) for kind,q,unit in sb))
    if fld=='cargo description':
        # Structured claims must agree when present in both; do not declare
        # equivalence just because the goods share a common brand string.
        def sig(t):
            inv=re.search(r'\bINVOICE\s+NO\.?\s*[:.]?\s*([A-Z0-9-]+)',t,re.I)
            hs=re.search(r'\bHS\s*CODE\s*[:.]?\s*([0-9][0-9.\-]+)',t,re.I)
            return ((inv.group(1).upper() if inv else None),
                    (hs.group(1).strip('.-') if hs else None))
        ia,ha=sig(a); ib,hb=sig(b)
        if ia and ib and ia!=ib:return False
        if ha and hb and ha!=hb:return False
        # PDFs may have extra packaging lines and attached clauses in SWB.
        # Only auto-match if source description words demonstrably occur in B
        # in order after normalizing punctuation. Otherwise flag as different.
        def core(t):
            t=re.sub(r'\bINVOICE\s+NO\.?\s*[:.]?\s*[A-Z0-9-]+','',t,flags=re.I)
            t=re.sub(r'\bHS\s*CODE\s*[:.]?\s*[0-9][0-9.\-]+','',t,flags=re.I)
            t=re.sub(r'\b\d[\d,]*\s*(?:T\s*\(\s*TYRES?\s*\)|PIECES?)\s*(?:OF)?','',t,flags=re.I)
            return re.findall(r'[A-Z]{2,}',t.upper())
        source=core(a); target=core(b)
        if not source:return None
        # A continuous ordered subsequence permits SWB packaging text around
        # the SI description but rejects a substituted country or goods type.
        return any(target[i:i+len(source)]==source for i in range(len(target)-len(source)+1))
    return normalized_value(a)==normalized_value(b)


def swb_inline_claims(exam_pdf, profile):
    """Extract additional invoice/HS/net-weight values visible inside SWB goods.

    The main profile's Cargo Description is the only eligible region: do not
    match invoice numbers appearing in unrelated clauses on other pages.
    """
    from waybill_rules import extract
    goods=extract(exam_pdf,{'Cargo Description'},profile).get('Cargo Description',{})
    items={'Invoice Number':r'\bINVOICE\s+NO\.?\s*[:.]?\s*([A-Z0-9-]+)',
           'HS Code':r'\bHS\s*CODE\s*[:.]?\s*([0-9][0-9.\-]+)',
           'Net Weight':r'\bNET\s+WEIGHT\s*[:.]?\s*([\d,.]+)\s*(KGS?)'}
    text=goods.get('text','')
    result={}
    for name,pattern in items.items():
        m=re.search(pattern,text,re.I)
        selected_words=[]
        if m:
            tokens=goods.get('words',[])
            # Inspect only a short window adjacent to the claim heading.
            start_keywords={'Invoice Number':'INVOICE','HS Code':'HS','Net Weight':'NET'}
            for ix,tok in enumerate(tokens):
                if tok['word'].upper().rstrip(':.')==start_keywords[name]:
                    selected_words=tokens[ix:ix+(3 if name=='Invoice Number' else 3 if name=='HS Code' else 5)]
                    break
        result[name]={'text': (' '.join(g for g in m.groups() if g) if m else ''),
                      'words':selected_words if m else [],
                      'valid':bool(m),'source':'SWB: Cargo Description'}
    return result


def enrich_one_address_continuations(exam_pdf, records):
    """Use explicit SH>/CN>/NP> continuation tags in ONE two-page drafts.

    Content is considered only inside the printed cargo-description column,
    between visible source markers; never guess missing continuation text.
    """
    with fitz.open(exam_pdf) as doc:
        if len(doc) < 2:
            return records
        page0 = _words(doc[0],0)
        page1 = _words(doc[1],1)
        marker0 = [w for w in page0 if w['word']=='SH>' and w['rect'].y0 > doc[0].rect.height*.4]
        marker1 = {w['word']:w for w in page1 if w['word'] in {'CN>','NP>'}}
        if not marker0 or 'CN>' not in marker1 or 'NP>' not in marker1:
            return records
        # Only supplement original field, never remove its native boxes.
        x0=.33*doc[1].rect.width; x1=.71*doc[1].rect.width
        p0start=max(w['rect'].y1 for w in marker0)
        tail0=_box(page0,.32*doc[0].rect.width,p0start+.2,
                   .71*doc[0].rect.width,p0start+19)
        marker_y=lambda name:marker1[name]['rect'].y0
        ship1=_box(page1,x0,doc[1].rect.height*.096,x1,marker_y('CN>')-1)
        consignee1=_box(page1,x0,marker1['CN>']['rect'].y1+.1,x1,marker_y('NP>')-1)
        notify1=_box(page1,x0,marker1['NP>']['rect'].y1+.1,x1,
                     min(doc[1].rect.height*.275,marker_y('NP>')+38))
        segments={'Shipper':[tail0,ship1], 'Consignee':[consignee1], 'Notify Party':[notify1]}
        for name, pieces in segments.items():
            extra=[w for piece in pieces for w in piece]
            if not extra or name not in records:
                continue
            line_text='\n'.join(_record(piece,source='SWB ONE continuation')['text']
                                for piece in pieces if piece)
            current=records[name]
            records[name]=dict(current,
                               text=current['text'].rstrip()+'\n'+line_text,
                               words=current['words']+extra)
    return records


def additional_claims(exam_pdf, profile, reference_records, selected=None, matched_locations=None):
    """Optional metadata-only audit of invoice/HS/net weight within SWB goods.

    Returns (issues, missing) without interpreting Packing List's creation
    date as a SWB's issue/on-board date.
    """
    from waybill_rules import WaybillDifference, _hits
    claimed=swb_inline_claims(exam_pdf,profile)
    issues=[];missing=[]
    wanted=set(selected) if selected is not None else {'Invoice Number','HS Code','Net Weight'}
    for field in ('Invoice Number','HS Code','Net Weight'):
        if field not in wanted: continue
        a=reference_records.get(field)
        b=claimed.get(field)
        if not a or not a.get('valid'):
            missing.append(f'{field}: nilai SI/PL tidak tersedia')
            continue
        if not b or not b.get('valid'):
            missing.append(f'{field}: tidak terbaca pada Cargo Description SWB')
            continue
        if field=='Net Weight':
            # Numeric equivalence with the printed KG/KGS quantity.
            same=equivalent('Gross Weight',a['text'],b['text'])
        else:
            same=re.sub(r'\s+','',a['text']).upper()==re.sub(r'\s+','',b['text']).upper()
        if same and matched_locations is not None:
            matched_locations.append({'field':field,
                'reference_text':str(a.get('text','')),
                'examined_text':str(b.get('text','')),
                'ref_hits':_hits(a['words'],0,len(a['words']),'Sama'),
                'exam_hits':_hits(b['words'],0,len(b['words']),'Sama')})
        if not same:
            diff=WaybillDifference('Perubahan',None,None,a['text'],b['text'],
                                  f'Rujukan {a["source"]}: {field}; Perubahan',False,field)
            issues.append((diff, ({'hits':_hits(a['words'],0,len(a['words']),'Perubahan')},
                                  {'hits':_hits(b['words'],0,len(b['words']),'Perubahan')})))
    return issues, missing
