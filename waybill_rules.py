"""Waybill preset for text-based PDF files. Offline, coordinate-based extraction.

Coordinates are relative to the first page. The template targets the ANL sea
waybill supplied for development; other templates require review/calibration.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import pymupdf as fitz

FIELDS = [
 ('Shipper',(.005,.018,.47,.110)),
 ('Consignee',(.005,.110,.47,.185)),
 ('Notify Party',(.005,.185,.47,.278)),
 ('Voyage Number',(.825,.018,.995,.042)),
 ('Waybill Number',(.825,.044,.995,.085)),
 ('Vessel',(.005,.302,.225,.342)),
 ('Port of Loading',(.225,.302,.47,.342)),
 ('Port of Discharge',(.47,.302,.735,.342)),
 ('Container & Seal',(.005,.37,.225,.685)),
 ('Cargo Description',(.225,.37,.72,.685)),
 ('Weight & Measurement',(.715,.37,.995,.685)),
 ('Place & Date of Issue',(.005,.925,.52,.958)),
 ('Additional Clauses',(.005,.69,.995,.925)),
]

@dataclass
class WaybillDifference:
    kind: str
    reference_index: int | None
    examined_index: int | None
    reference_text: str
    examined_text: str
    detail: str
    apply: bool = False  # field extraction cannot safely reconstruct the source PDF
    field: str = ''


def _normalize(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip().casefold()


def _rect(page, bounds):
    r=page.rect
    return fitz.Rect(r.x0+bounds[0]*r.width,r.y0+bounds[1]*r.height,
                     r.x0+bounds[2]*r.width,r.y0+bounds[3]*r.height)


def extract(path, chosen=None):
    """Returns field -> {text, page, rect}; excludes labels where possible."""
    chosen=set(chosen or [name for name,_ in FIELDS]); result={}
    with fitz.open(path) as doc:
        if not doc: raise ValueError('PDF kosong')
        page=doc[0]
        for name,bounds in FIELDS:
            if name not in chosen: continue
            if name=='Additional Clauses':
                parts=[]
                for pno,p in enumerate(doc):
                    region=_rect(p,bounds if pno==0 else (.005,.69,.995,.925))
                    text=p.get_text('text',clip=region,sort=True).strip()
                    if text: parts.append(text)
                value='\n'.join(parts)
            else:
                region=_rect(page,bounds)
                value=page.get_text('text',clip=region,sort=True).strip()
            result[name]={'text':value,'page':0,'rect':region if name=='Additional Clauses' else _rect(page,bounds)}
    return result


def compare_waybills(reference_pdf, examined_pdf, selected=None):
    selected=set(selected or [name for name,_ in FIELDS])
    a=extract(reference_pdf,selected);b=extract(examined_pdf,selected)
    differences=[]; locations=[]
    for name,_ in FIELDS:
        if name not in selected: continue
        left=a[name]['text'];right=b[name]['text']
        if _normalize(left)==_normalize(right):continue
        kind='Perubahan' if left and right else ('Hilang' if left else 'Berlebih')
        differences.append(WaybillDifference(kind,None,None,left,right,
                           'Field Waybill: '+name+' (perlu verifikasi visual)',False,name))
        locations.append((a[name],b[name]))
    return differences,locations
