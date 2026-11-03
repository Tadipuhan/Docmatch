"""Precise token-level highlights for ANL Waybill PDF. All processing offline."""
from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import pymupdf as fitz

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

# Carrier-specific coordinate templates (relative to the PDF page). The ANL
# template is kept untouched for backwards compatibility.
EVERGREEN_FIELDS = {
 'Shipper':(.02,.085,.54,.155), 'Consignee':(.02,.155,.56,.245),
 'Notify Party':(.02,.245,.56,.34), 'Voyage Number':(.02,.34,.32,.395),
 'Waybill Number':(.54,.07,.995,.115), 'Vessel':(.02,.34,.32,.395),
 'Port of Loading':(.31,.34,.56,.405), 'Port of Discharge':(.02,.395,.32,.445),
 'Container & Seal':(.02,.445,.34,.69), 'Cargo Description':(.34,.445,.79,.77),
 'Weight & Measurement':(.78,.435,.995,.60),
 'Place & Date of Issue':(.23,.86,.62,.95), 'Additional Clauses':(.02,.69,.995,.97),
}
GSL_FIELDS = {
 'Shipper':(.055,.075,.53,.145), 'Consignee':(.055,.145,.53,.24),
 'Notify Party':(.055,.245,.53,.34), 'Voyage Number':(.29,.34,.54,.41),
 'Waybill Number':(.53,.07,.995,.14), 'Vessel':(.055,.34,.36,.41),
 'Port of Loading':(.30,.34,.54,.44), 'Port of Discharge':(.055,.41,.36,.48),
 'Container & Seal':(.055,.46,.33,.72), 'Cargo Description':(.32,.46,.80,.72),
 'Weight & Measurement':(.77,.46,.995,.74),
 'Place & Date of Issue':(.56,.83,.995,.94), 'Additional Clauses':(.055,.70,.995,.97),
}

# Override the old extract/compare with profile-aware equivalents while
# preserving the original public signatures and difference structure.

def _profile_regions(profile):
    if profile in ('waybill','waybill_anl',None): return dict(FIELDS)
    if profile=='waybill_evergreen': return EVERGREEN_FIELDS
    if profile=='waybill_gsl': return GSL_FIELDS
    raise ValueError('Preset SWB tidak dikenal: '+str(profile))

def _readable_ratio(words):
    tokens=[w['word'] for w in words]
    if not tokens:return 0.0
    # Reject garbled character maps: punctuation-only or mostly nonletters.
    good=sum(bool(re.search(r'[A-Za-z]{2,}|\d{3,}',t)) for t in tokens)
    return good/len(tokens)

def extract(path, chosen=None, profile='waybill_anl'):
    regions=_profile_regions(profile)
    chosen=set(chosen) if chosen is not None else set(regions)
    result={}
    with fitz.open(path) as doc:
        if not len(doc): raise ValueError('PDF kosong')
        if profile=='waybill_gsl':
            allwords=[{'word':str(w[4])} for p in doc for w in p.get_text('words')]
            if _readable_ratio(allwords)<.35:
                raise ValueError('PDF Golden Star Line menggunakan encoding font yang tidak terbaca. '
                                 'Perbandingan dihentikan untuk mencegah temuan palsu. '
                                 'Gunakan PDF dengan lapisan teks Unicode yang valid; OCR belum didukung.')
        for name,bounds in regions.items():
            if name not in chosen:continue
            words=[]
            # Supplementary sheets are compared as clauses/cargo, not as the
            # first-page fields; no arbitrary content is attributed to Shipper.
            pages=range(len(doc)) if name=='Additional Clauses' else [0]
            for page_no in pages:
                page=doc[page_no]
                region=_rect(page,bounds if page_no==0 else (.02,.07,.99,.97))
                for w in page.get_text('words',clip=region,sort=True):
                    token=str(w[4]).strip()
                    if token: words.append({'word':token,'rect':fitz.Rect(w[:4]),'page':page_no})
            result[name]={'text':' '.join(w['word'] for w in words),'words':words}
    return result

def compare_waybills(reference_pdf, examined_pdf, selected=None, profile='waybill_anl'):
    regions=_profile_regions(profile)
    selected=set(selected) if selected is not None else set(regions)
    ref=extract(reference_pdf,selected,profile); exam=extract(examined_pdf,selected,profile)
    differences=[];locations=[]
    for name in regions:
        if name not in selected:continue
        a=ref[name]['words'];b=exam[name]['words']
        matcher=SequenceMatcher(None,[_norm(w['word']) for w in a],[_norm(w['word']) for w in b],autojunk=False)
        for op,i1,i2,j1,j2 in matcher.get_opcodes():
            if op=='equal':continue
            kind={'replace':'Perubahan','delete':'Hilang','insert':'Berlebih'}[op]
            differences.append(WaybillDifference(kind,None,None,
                ' '.join(w['word'] for w in a[i1:i2]),
                ' '.join(w['word'] for w in b[j1:j2]),
                'Field Waybill: '+name+'; '+kind,False,name))
            locations.append(({'hits':_hits(a,i1,i2,kind)}, {'hits':_hits(b,j1,j2,kind)}))
    return differences,locations
