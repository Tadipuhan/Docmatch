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
