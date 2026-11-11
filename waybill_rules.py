"""Precise token-level highlights for ANL Waybill PDF. All processing offline."""
from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import pymupdf as fitz
from gsl_font_recovery import recover_gsl_field, UnrecoverableGSLText
from gsl_ocr import PageOCR, recover_field as recover_ocr_field, OCRError

GSL_SKIPPED_FIELDS = []
GSL_DIAGNOSTICS = {}

FIELDS = [
 ('Shipper',(.005,.018,.47,.110)), ('Consignee',(.005,.110,.47,.185)),
 ('Notify Party',(.005,.185,.47,.278)), ('Voyage Number',(.825,.018,.995,.042)),
 ('Waybill Number',(.825,.044,.995,.085)), ('Vessel',(.005,.302,.225,.342)),
 ('Port of Loading',(.225,.302,.47,.342)), ('Port of Discharge',(.47,.302,.735,.342)),
 ('Container & Seal',(.005,.37,.225,.685)), ('Cargo Description',(.225,.37,.72,.685)),
 ('Weight & Measurement',(.715,.37,.995,.685)), ('Place & Date of Issue',(.005,.925,.52,.958)),
 ('Additional Clauses',(.005,.69,.995,.925)),
]
@dataclass
class WaybillDifference:
    kind:str
    reference_index:int|None
    examined_index:int|None
    reference_text:str
    examined_text:str
    detail:str
    apply:bool=False
    field:str=''

def _rect(page,bounds):
    r=page.rect
    return fitz.Rect(r.x0+bounds[0]*r.width,r.y0+bounds[1]*r.height,r.x0+bounds[2]*r.width,r.y0+bounds[3]*r.height)

def _norm(word):
    return re.sub(r'\s+','',word).casefold()

def extract(path,chosen=None):
    chosen=set(chosen) if chosen is not None else {name for name,_ in FIELDS}
    result={}
    with fitz.open(path) as doc:
        if len(doc)==0:raise ValueError('PDF kosong')
        for name,bounds in FIELDS:
            if name not in chosen:continue
            words=[]
            page_ids=range(len(doc)) if name=='Additional Clauses' else [0]
            for page_no in page_ids:
                page=doc[page_no]
                region=_rect(page,bounds if page_no==0 else (.005,.69,.995,.925))
                for w in page.get_text('words',clip=region,sort=True):
                    if len(w)<5:continue
                    token=str(w[4]).strip()
                    if token:
                        words.append({'word':token,'rect':fitz.Rect(w[:4]),'page':page_no})
            result[name]={'text':' '.join(w['word'] for w in words),'words':words}
    return result

def _hits(words,start,end,kind):
    # Preserve each individual PDF word bounding box. No whole-field overlays.
    return [{'page':w['page'],'rect':w['rect'],'kind':kind} for w in words[start:end]]

def compare_waybills(reference_pdf, examined_pdf, selected=None):
    """Return one auditable discrepancy per edit opcode, with matching PDF marks."""
    selected=set(selected) if selected is not None else {name for name,_ in FIELDS}
    ref=extract(reference_pdf,selected); exam=extract(examined_pdf,selected)
    differences=[]; locations=[]
    for name,_ in FIELDS:
        if name not in selected:continue
        a=ref[name]['words']; b=exam[name]['words']
        matcher=SequenceMatcher(None,[_norm(w['word']) for w in a],[_norm(w['word']) for w in b],autojunk=False)
        for op,i1,i2,j1,j2 in matcher.get_opcodes():
            if op=='equal':continue
            kind={'replace':'Perubahan','delete':'Hilang','insert':'Berlebih'}[op]
            reference_text=' '.join(w['word'] for w in a[i1:i2])
            examined_text=' '.join(w['word'] for w in b[j1:j2])
            differences.append(WaybillDifference(kind,None,None,reference_text,examined_text,
                               'Field Waybill: '+name+'; '+kind,False,name))
            locations.append(({'hits':_hits(a,i1,i2,kind)}, {'hits':_hits(b,j1,j2,kind)}))
    return differences,locations

# Page-specific, non-overlapping cells calibrated against the supplied SWB samples.
# Each entry: (page index, x0, y0, x1, y1) in normalized page coordinates.
# This is a fixed-layout preset, not OCR or universal form recognition.
EVERGREEN_CELLS = {
 'Shipper':[(0,.025,.084,.55,.157)],
 'Consignee':[(0,.025,.165,.55,.241)],
 'Notify Party':[(0,.025,.241,.55,.319)],
 'Document Number':[(0,.555,.082,.98,.112)],
 'Export References':[(0,.555,.112,.98,.148)],
 'Pre-Carriage':[(0,.025,.339,.305,.365)],
 'Place of Receipt':[(0,.307,.339,.55,.365)],
 'Vessel':[(0,.025,.367,.16,.392)],
 'Voyage Number':[(0,.162,.367,.305,.392)],
 'Port of Loading':[(0,.307,.367,.55,.392)],
 'Port of Discharge':[(0,.025,.394,.305,.42)],
 'Place of Delivery':[(0,.307,.394,.55,.42)],
 'Container & Seal':[(0,.025,.47,.35,.615)],
 'Cargo Description':[(0,.35,.47,.78,.612)],
 'Attached List':[(1,.025,.065,.98,.72)],
 'Weight & Measurement':[(0,.78,.435,.98,.48)],
 'Freight & Charges':[(0,.025,.69,.78,.80)],
 'Waybill Number':[(0,.025,.839,.235,.871)],
 'Place & Date of Issue':[(0,.235,.865,.50,.892)],
 'Additional Clauses':[(0,.78,.612,.98,.705),(1,.025,.72,.98,.96)],
}
# The GSL sample's embedded text is corrupt; these cells describe its visual
# layout only. Extraction remains blocked until a readable text-layer PDF is used.
# v1.8.2: each selectable GSL field is mapped to one printed box / column.
# Normalized bounds (x0,y0,x1,y1). Page 2 (index 1) is blank in the
# supplied three-page samples; the attached-list form is on index 2.
# These are template-specific regions and must be recalibrated for new layouts.
GSL_CELLS = {
 'Shipper':[(0,.07,.073,.49,.144)],
 'Consignee':[(0,.07,.146,.49,.233)],
 'Notify Party':[(0,.07,.237,.49,.341)],
 'Booking Number':[(0,.49,.073,.69,.105)],
 'Waybill Number':[(0,.69,.073,.98,.105)],
 # Vessel and voyage share a printed box; use token classification below.
 'Vessel':[(0,.07,.347,.29,.383)],
 'Voyage Number':[(0,.07,.347,.29,.383)],
 'Port of Loading':[(0,.29,.347,.54,.383)],
 'Port of Discharge':[(0,.07,.383,.29,.421)],
 'Final Destination':[(0,.29,.383,.54,.421)],
 # Main-page cargo table: distinct columns, not a combined full-width field.
 'Main - Container & Seal':[(0,.07,.434,.30,.67)],
 'Main - Cargo Description':[(0,.30,.434,.76,.67)],
 'Main - Gross Weight':[(0,.76,.434,.87,.69)],
 'Main - Measurement':[(0,.87,.434,.98,.69)],
 'Main - Clauses':[(0,.07,.70,.65,.94)],
 'Place & Date of Issue':[(0,.65,.855,.98,.928)],
 # Page 3: six non-overlapping logical boxes, aligned with the printed form.
 # Top table is split into three columns; the three lower bands are independent.
 'Attached List - MKS & NOS/SEAL.NO':[(2,.07,.155,.258,.392)],
 'Attached List - Description of Goods':[(2,.258,.155,.680,.392)],
 'Attached List - Weight & Measurement':[(2,.680,.155,.975,.392)],
 'Attached List - CONT & SEAL':[(2,.07,.392,.975,.420)],
 "Attached List - SHIPPER'S LOAD STOWAGE & COUNT":[(2,.07,.420,.975,.505)],
 'Attached List - CLAUSES':[(2,.07,.525,.975,.720)],
}

GSL_FIELD_GROUPS = {
 'Identitas & Nomor': ['Shipper','Consignee','Notify Party','Booking Number','Waybill Number'],
 'Perjalanan': ['Vessel','Voyage Number','Port of Loading','Port of Discharge','Final Destination'],
 'Halaman Utama - Kotak Muatan': ['Main - Container & Seal','Main - Cargo Description','Main - Gross Weight','Main - Measurement','Main - Clauses','Place & Date of Issue'],
 'Halaman 3 - Attached List': ['Attached List - Header','Attached List - MKS & NOS/SEAL.NO','Attached List - Description of Goods','Attached List - Weight & Measurement','Attached List - CONT & SEAL',"Attached List - SHIPPER'S LOAD STOWAGE & COUNT",'Attached List - CLAUSES'],
}


def profile_field_names(profile='waybill_anl'):
    if profile=='waybill_evergreen':return list(EVERGREEN_CELLS)
    if profile=='waybill_gsl':return list(GSL_CELLS)
    return [name for name,_ in FIELDS]

def _profile_cells(profile):
    if profile in ('waybill','waybill_anl',None):
        return {name:[(0,*bounds)] for name,bounds in FIELDS}
    if profile=='waybill_evergreen':return EVERGREEN_CELLS
    if profile=='waybill_gsl':return GSL_CELLS
    raise ValueError('Preset SWB tidak dikenal: '+str(profile))

def _readable_ratio(words):
    if not words:return 0.0
    return sum(bool(re.search(r'[A-Za-z]{2,}|\d{3,}',w['word'])) for w in words)/len(words)

_extract_anl=extract

def extract(path,chosen=None,profile='waybill_anl'):
    if profile in ('waybill','waybill_anl',None):
        return _extract_anl(path,chosen)
    cells=_profile_cells(profile)
    chosen=set(chosen) if chosen is not None else set(cells)
    result={}
    with fitz.open(path) as doc:
        if not doc:raise ValueError('PDF kosong')
        if profile=='waybill_gsl' and len(doc)<3:
            raise ValueError('Preset GSL memerlukan halaman Attached List pada halaman PDF ke-3. Dokumen ini hanya memiliki %d halaman.' % len(doc))
        ocr_engine = PageOCR(doc) if profile=='waybill_gsl' else None
        for name,regions in cells.items():
            if name not in chosen:continue
            if profile=='waybill_gsl':
                # v1.8: OCR is the PRIMARY reader for every GSL field.
                # Never use Type3 recovery as a silent fallback: it made the
                # application appear to run OCR while retaining old results.
                try:
                    recovered = recover_ocr_field(doc, regions, _rect, ocr_engine)
                except OCRError as exc:
                    recovered = {'text':'', 'words':[], 'valid':False, 'reason':str(exc)}
                recovered['source'] = 'OCR'
                words = recovered.get('words', [])
                # Separate vessel and voyage when both share a printed cell.
                if name in ('Vessel','Voyage Number') and words:
                    voyage = lambda token: bool(re.fullmatch(r'[A-Z]?\d{2,4}[A-Z]?', token.upper()))
                    words = [w for w in words if voyage(w['word']) == (name=='Voyage Number')]
                if words and name in ('Shipper','Consignee','Notify Party','Booking Number','Waybill Number','Vessel','Voyage Number','Port of Loading','Port of Discharge','Final Destination'):
                    # Remove only known printed label words at the very top of the cell.
                    # Do not delete arbitrary data containing the same words later.
                    labels = {
                        'Shipper': {'SHIPPER','EXPORTER','NAME','ADDRESS'},
                        'Consignee': {'CONSIGNEE','NAME','ADDRESS'},
                        'Notify Party': {'NOTIFY','PARTY','NAME','ADDRESS','NON-NEGOTIABLE'},
                        'Booking Number': {'BOOKING','NO'},
                        'Waybill Number': {'WAYBILL','NO'},
                        'Vessel': {'VESSEL'}, 'Voyage Number': {'VOYAGE'},
                        'Port of Loading': {'PORT','OF','LOADING'},
                        'Port of Discharge': {'PORT','OF','DESTINATION','DISCHARGE'},
                        'Final Destination': {'FINAL','DESTINATION'},
                    }.get(name, set())
                    top = min(w['rect'].y0 for w in words)
                    line_height = max(6.0, min(13.0, (sum(w['rect'].height for w in words) / len(words)) * 1.25))
                    kept = []
                    for w in words:
                        clean = re.sub(r'[^A-Z-]', '', w['word'].upper())
                        if w['rect'].y0 <= top + line_height and clean in labels:
                            continue
                        kept.append(w)
                    if kept: words = kept
                if words:
                    mean = sum(w['confidence'] for w in words)/len(words)
                    recovered.update(words=words, text=' '.join(w['word'] for w in words),
                                     confidence=mean, valid=mean >= 55)
                    if mean < 55:
                        recovered['reason'] = f'Confidence OCR {mean:.0f} di bawah batas 55'
                else:
                    recovered.update(words=[],text='',valid=False,
                                     reason='Tidak ada token OCR tervalidasi di kotak field')
                result[name] = recovered
                continue
            words=[]
            for page_no,*bounds in regions:
                if page_no>=len(doc):continue
                page=doc[page_no]
                for w in page.get_text('words',clip=_rect(page,bounds),sort=True):
                    token=str(w[4]).strip()
                    if token:words.append({'word':token,'rect':fitz.Rect(w[:4]),'page':page_no})
            result[name]={'text':' '.join(w['word'] for w in words),'words':words}
    return result

def compare_waybills(reference_pdf,examined_pdf,selected=None,profile='waybill_anl'):
    cells=_profile_cells(profile)
    selected=set(selected) if selected is not None else set(cells)
    global GSL_SKIPPED_FIELDS, GSL_DIAGNOSTICS
    GSL_SKIPPED_FIELDS = []
    GSL_DIAGNOSTICS = {}
    ref=extract(reference_pdf,selected,profile)
    exam=extract(examined_pdf,selected,profile)
    differences=[];locations=[]
    for name in cells:
        if name not in selected:continue
        if profile=='waybill_gsl':
            GSL_DIAGNOSTICS[name] = {'rujukan': {'valid': ref[name].get('valid'), 'text': ref[name].get('text',''), 'words': ref[name].get('words',[]), 'reason': ref[name].get('reason',''), 'source': ref[name].get('source','')}, 'diperiksa': {'valid': exam[name].get('valid'), 'text': exam[name].get('text',''), 'words': exam[name].get('words',[]), 'reason': exam[name].get('reason',''), 'source': exam[name].get('source','')}}
            if (ref[name].get('valid') is False or exam[name].get('valid') is False or not ref[name]['words'] or not exam[name]['words']):
                GSL_SKIPPED_FIELDS.append(name)
                continue
        a=ref[name]['words'];b=exam[name]['words']
        matcher=SequenceMatcher(None,[_norm(w['word']) for w in a],[_norm(w['word']) for w in b],autojunk=False)
        for op,i1,i2,j1,j2 in matcher.get_opcodes():
            if op=='equal':continue
            kind={'replace':'Perubahan','delete':'Hilang','insert':'Berlebih'}[op]
            differences.append(WaybillDifference(kind,None,None,' '.join(w['word'] for w in a[i1:i2]),
                ' '.join(w['word'] for w in b[j1:j2]),'Field Waybill: '+name+'; '+kind + ('; OCR — verifikasi manual' if profile=='waybill_gsl' and (ref[name].get('source')=='OCR' or exam[name].get('source')=='OCR') else ''),False,name))
            locations.append(({'hits':_hits(a,i1,i2,kind)}, {'hits':_hits(b,j1,j2,kind)}))
    return differences,locations
