"""Precise token-level highlights for ANL Waybill PDF. All processing offline."""
from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import pymupdf as fitz
from gsl_font_recovery import recover_page_words, recover_gsl_field, UnrecoverableGSLText, word_anchor
from gsl_layout import GSL_BOXES, boxes_for_page
from textnorm import normalize_text
from flexible_reference import detect_flexible_pdf, extract_flexible
from anl_form import ANL_FIELDS, extract_anl_form
from anl_semantics import fields_equal

GSL_SKIPPED_FIELDS = []
GSL_DIAGNOSTICS = {}
REFERENCE_NEEDS_REVIEW = []
REFERENCE_EXTRACTION_DIAGNOSTICS = {}

# Profil ANL/CNC/CMA CGM: kotak NILAI (tanpa caption) didefinisikan di anl_form.ANL_FIELDS.
FIELDS = list(ANL_FIELDS)
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
    """Ekstraksi formulir ANL/CNC/CMA CGM (v1.8.33.2: anl_form, tanpa caption, jangkar footer)."""
    with fitz.open(path) as doc:
        return extract_anl_form(doc,chosen)

def _hits(words,start,end,kind):
    # Preserve each individual PDF word bounding box. No whole-field overlays.
    return [{'page':w['page'],'rect':w['rect'],'kind':kind} for w in words[start:end]]

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
# Ocean Network Express (ONE) draft: PDF-native text, normalized page-one boxes.
# Calibrated using two 2-page examples: ONEYJKTG94494400 (Sea Waybill),
# ONEYJKTGA3152700 (Bill of Lading). The two document types share layout.
# Only the VALUE region is selected, not its printed label. Optional blank
# fields remain empty. Coordinates are fractions of each PDF page.
ONE_CELLS = {
 'Shipper': [(0,.047,.083,.55,.141)],
 'Booking Number': [(0,.57,.079,.781,.097)],
 'Waybill Number': [(0,.792,.079,.989,.097)],
 'Consignee': [(0,.047,.166,.553,.222)],
 'Notify Party': [(0,.047,.244,.55,.309)],
 'Export References': [(0,.575,.105,.985,.145)],
 'Forwarding Agent': [(0,.575,.175,.82,.197)],
 'Pre-Carriage': [(0,.047,.324,.298,.340)],
 'Place of Receipt': [(0,.305,.325,.562,.340)],
 'Vessel / Voyage': [(0,.047,.350,.300,.369)],
 'Port of Loading': [(0,.305,.352,.562,.369)],
 'Final Destination': [(0,.568,.351,.984,.369)],
 'Port of Discharge': [(0,.047,.381,.298,.398)],
 'Place of Delivery': [(0,.305,.381,.563,.398)],
 'Type of Movement': [(0,.568,.38,.980,.397)],
 'Container & Seal': [(0,.047,.429,.253,.455)],
 'Quantity': [(0,.289,.461,.354,.481)],
 'Cargo Description': [(0,.357,.463,.748,.606)],
 'Gross Weight': [(0,.746,.46,.865,.481)],
 'Gross Measurement': [(0,.872,.46,.988,.481)],
 'Freight Payable At': [(0,.047,.659,.34,.669)],
 'Service Contract Number': [(0,.365,.655,.515,.667)],
 'Freight & Charges': [(0,.047,.68,.808,.808)],
 'Date Laden On Board': [(0,.817,.747,.983,.76)],
 'Place & Date of Issue': [(0,.817,.772,.983,.783),(0,.817,.798,.983,.811)],
 'Attached List - Description of Goods': [(1,.334,.065,.708,.275)],
 'Attached List - Clauses': [(1,.045,.291,.708,.53)],
}
ONE_FIELD_GROUPS = {
 'Halaman 1 - Identitas': ['Shipper','Booking Number','Waybill Number','Consignee','Notify Party','Export References','Forwarding Agent'],
 'Halaman 1 - Rute': ['Pre-Carriage','Place of Receipt','Vessel / Voyage','Port of Loading','Final Destination','Port of Discharge','Place of Delivery','Type of Movement'],
 'Halaman 1 - Muatan': ['Container & Seal','Quantity','Cargo Description','Gross Weight','Gross Measurement'],
 'Halaman 1 - Freight & Penerbitan': ['Freight Payable At','Service Contract Number','Freight & Charges','Date Laden On Board','Place & Date of Issue'],
 'Halaman 2 - Attached List': ['Attached List - Description of Goods','Attached List - Clauses'],
}

# Maersk B/L and Non-Negotiable Waybill have two distinct first-page layouts.
# Values below are normalized coordinates validated against two provided PDFs.
# FINAL puts Notify Party in the RIGHT column; DRAFT puts it in the LEFT column.
# Do not re-use one variant blindly: the vessel and cargo grids shift vertically.
MAERSK_FINAL_CELLS = {
 'Shipper':[(0,.058,.088,.495,.156)],
 'Booking Number':[(0,.505,.090,.68,.102)],
 'Waybill Number':[(0,.855,.065,.984,.077)],
 'Service Contract Number':[(0,.873,.116,.987,.130)],
 'Consignee':[(0,.058,.178,.497,.235)],
 'Notify Party':[(0,.505,.171,.986,.238)],
 'Vessel':[(0,.057,.254,.266,.266)],
 'Voyage Number':[(0,.267,.254,.480,.266)],
 'Port of Loading':[(0,.057,.285,.266,.297)],
 'Port of Discharge':[(0,.267,.285,.497,.297)],
 'Place of Receipt':[(0,.507,.254,.987,.267)],
 'Place of Delivery':[(0,.507,.285,.987,.298)],
 'Quantity':[(0,.062,.338,.465,.351)],
 'Cargo Description':[(0,.062,.362,.670,.400)],
 'Container & Seal':[(0,.062,.408,.694,.423)],
 'Gross Weight':[(0,.693,.325,.826,.338)],
 'Gross Measurement':[(0,.836,.325,.984,.338)],
 'Freight & Charges':[(0,.055,.651,.978,.725)],
 "Carrier's Receipt":[(0,.058,.760,.270,.773)],
 'Place of Issue':[(0,.277,.753,.497,.766)],
 'Date of Issue':[(0,.277,.783,.497,.796)],
 'Shipped on Board Date':[(0,.277,.815,.497,.829)],
 'Original Bills':[(0,.058,.782,.265,.796)],
 'Attached List - Clauses':[(1,.04,.08,.90,.62)],
}
MAERSK_DRAFT_CELLS = {
 'Shipper':[(0,.062,.090,.499,.162)],
 'Booking Number':[(0,.509,.089,.680,.102)],
 'Waybill Number':[(0,.855,.065,.984,.077)],
 'Service Contract Number':[(0,.867,.116,.989,.130)],
 'Consignee':[(0,.057,.171,.500,.244)],
 'Notify Party':[(0,.057,.255,.501,.326)],
 'Vessel':[(0,.058,.334,.300,.346)],
 'Voyage Number':[(0,.300,.334,.496,.346)],
 'Port of Loading':[(0,.058,.362,.300,.374)],
 'Port of Discharge':[(0,.300,.362,.500,.374)],
 'Place of Receipt':[(0,.507,.334,.989,.347)],
 'Place of Delivery':[(0,.507,.362,.989,.375)],
 'Quantity':[(0,.063,.441,.500,.454)],
 'Cargo Description':[(0,.062,.465,.670,.600)],
 'Container & Seal':[(0,.062,.607,.693,.634)],
 'Gross Weight':[(0,.690,.404,.823,.417)],
 'Gross Measurement':[(0,.824,.404,.983,.417)],
 'Freight & Charges':[(0,.057,.724,.976,.763),(1,.057,.736,.976,.85)],
 "Carrier's Receipt":[(0,.074,.779,.268,.793)],
 'Place of Issue':[(0,.272,.774,.493,.788)],
 'Date of Issue':[(0,.272,.800,.495,.812)],
 'Shipped on Board Date':[(0,.072,.804,.267,.817)],
 'Original Bills':[(0,.057,.806,.267,.818)],
 'Attached List - Clauses':[(1,.045,.084,.89,.42)],
}
MAERSK_CELLS = MAERSK_FINAL_CELLS
MAERSK_FIELD_GROUPS = {
 'Identitas & Pihak': ['Shipper','Booking Number','Waybill Number','Service Contract Number','Consignee','Notify Party'],
 'Kapal & Rute': ['Vessel','Voyage Number','Port of Loading','Port of Discharge','Place of Receipt','Place of Delivery'],
 'Muatan & Freight': ['Quantity','Cargo Description','Container & Seal','Gross Weight','Gross Measurement','Freight & Charges'],
 'Penerbitan': ["Carrier's Receipt",'Place of Issue','Date of Issue','Shipped on Board Date','Original Bills'],
 'Lampiran Halaman 2': ['Attached List - Clauses'],
}

def maersk_layout(page):
    """Detect first-page variant from the *printed Notify Party heading*, not filename."""
    for word in page.get_text('words',sort=True):
        if str(word[4]).casefold().rstrip(':') != 'notify':
            continue
        y = word[1] / page.rect.height
        if .14 < y < .33:
            return 'final' if word[0] / page.rect.width > .45 else 'draft'
    # No reliable anchor: avoid fabricating a template match.
    return None

def maersk_cells_for_page(page):
    layout = maersk_layout(page)
    if layout is None:
        raise ValueError('Layout MAERSK tidak dikenali: heading Notify Party tidak ditemukan')
    return MAERSK_FINAL_CELLS if layout == 'final' else MAERSK_DRAFT_CELLS

# PT Meratus Line: separate values-only geometries for the traditional one-page
# BILL OF LADING and the newer WAY BILL with possible continuation/T&C pages.
# Calibrated on two supplied native-text PDFs; coordinates are page fractions.
# Labels, boilerplate on the right side, and watermarks are excluded.
MERATUS_BL_CELLS = {
 'Waybill Number': [(0,.715,.010,.985,.025)],
 'Shipper': [(0,.031,.026,.533,.085)],
 'Consignee': [(0,.031,.120,.525,.177)],
 'Notify Party': [(0,.031,.212,.522,.231)],
 'Pre-Carriage': [(0,.031,.310,.297,.329)],
 'Place of Receipt': [(0,.317,.311,.550,.329)],
 'Vessel': [(0,.031,.341,.259,.361)],
 'Voyage Number': [(0,.266,.341,.375,.361)],
 'Port of Loading': [(0,.390,.341,.528,.361)],
 'Port of Discharge': [(0,.031,.374,.295,.393)],
 'Place of Delivery': [(0,.317,.374,.553,.393)],
 'Final Destination': [(0,.79,.374,.988,.393)],
 'Container & Seal': [(0,.026,.437,.349,.465)],
 'Container Count': [(0,.318,.687,.375,.699)],
 'Quantity': [(0,.399,.458,.488,.475)],
 'Cargo Description': [(0,.368,.454,.739,.551)],
 'Gross Weight': [(0,.740,.432,.823,.457)],
 'Gross Measurement': [(0,.844,.432,.921,.457)],
 'Freight & Charges': [(0,.327,.745,.983,.838)],
 'Freight Payable At': [(0,.350,.855,.49,.880)],
 'Place of Issue': [(0,.620,.855,.790,.881)],
 'Date of Issue': [(0,.782,.858,.874,.880)],
 'Original Bills': [(0,.345,.894,.620,.915)],
 'Shipped on Board Date': [(0,.128,.940,.215,.959)],
}
MERATUS_SWB_CELLS = {
 'Waybill Number': [(0,.689,.110,.832,.125)],
 'Shipper': [(0,.053,.066,.530,.124)],
 'Consignee': [(0,.053,.176,.450,.213)],
 'Notify Party': [(0,.053,.288,.452,.322)],
 'Pre-Carriage': [(0,.053,.402,.233,.422)],
 'Vessel': [(0,.237,.401,.400,.421)],
 'Voyage Number': [(0,.406,.401,.485,.421)],
 'Final Destination': [(0,.504,.402,.722,.421)],
 'Term': [(0,.727,.401,.801,.421)],
 'Reference Number': [(0,.801,.401,.95,.421)],
 'Place of Receipt': [(0,.053,.439,.226,.460)],
 'Port of Loading': [(0,.238,.439,.400,.460)],
 'Port of Discharge': [(0,.505,.439,.714,.460)],
 'Place of Delivery': [(0,.727,.439,.936,.460)],
 'Container & Seal': [(0,.053,.536,.334,.559)],
 'Container Count': [(0,.455,.503,.684,.522)],
 'Quantity': [(0,.430,.538,.493,.554)],
 'Cargo Description': [(0,.433,.538,.704,.612)],
 'Gross Weight': [(0,.700,.536,.792,.556)],
 'Gross Measurement': [(0,.865,.536,.945,.556)],
 'Freight & Charges': [(0,.350,.743,.982,.803)],
 'Freight Payable At': [(0,.053,.813,.280,.836)],
 'Original Bills': [(0,.296,.813,.575,.836)],
 'Shipped on Board Date': [(0,.053,.848,.325,.870)],
 'Place & Date of Issue': [(0,.326,.848,.730,.870)],
 'Attached List - Description of Goods': [(1,.443,.284,.745,.365)],
}
MERATUS_FIELD_GROUPS = {
 'Halaman 1 - Identitas': ['Waybill Number','Shipper','Consignee','Notify Party'],
 'Halaman 1 - Kapal & Rute': ['Pre-Carriage','Vessel','Voyage Number','Place of Receipt','Port of Loading','Port of Discharge','Place of Delivery','Final Destination','Term','Reference Number'],
 'Halaman 1 - Muatan': ['Container & Seal','Container Count','Quantity','Cargo Description','Gross Weight','Gross Measurement'],
 'Halaman 1 - Freight & Penerbitan': ['Freight & Charges','Freight Payable At','Original Bills','Shipped on Board Date','Place of Issue','Date of Issue','Place & Date of Issue'],
 'Lampiran (bila tersedia)': ['Attached List - Description of Goods'],
}
# Union of both variants: fields that do not exist on one variant remain empty.
MERATUS_CELLS = dict(MERATUS_BL_CELLS)
MERATUS_CELLS.update(MERATUS_SWB_CELLS)

def meratus_layout(page):
    """Use native-text headings and first-page geometry, never the filename."""
    words=page.get_text('words',sort=True)
    for w in words:
        if str(w[4]).casefold().strip(':')=='shipper' and w[0] < page.rect.width*.20:
            y=w[1]/page.rect.height
            if .005 < y < .04:return 'bl'
            if .04 <= y < .10:return 'swb'
    raise ValueError('Layout MERATUS belum dikenali: heading Shipper di luar posisi yang didukung')

def meratus_cells_for_page(page):
    return MERATUS_BL_CELLS if meratus_layout(page)=='bl' else MERATUS_SWB_CELLS


# Mediterranean Shipping Company (MSC) Sea Waybill / Bill of Lading.
# Both supplied documents use the same normalized front-page form. MSC may
# issue a separate RIDER PAGE for container detail; never read T&C as cargo.
# Bounding boxes contain VALUES, excluding nearby printed labels.
MSC_FRONT_CELLS = {
 'Waybill Number':[(0,.786,.024,.960,.041)],
 'Document Type':[(0,.519,.024,.700,.041)],
 'Shipper':[(0,.037,.092,.480,.142)],
 'Consignee':[(0,.037,.151,.481,.205)],
 'Notify Party':[(0,.037,.223,.489,.277)],
 'Vessel / Voyage':[(0,.040,.295,.350,.310)],
 'Booking Number':[(0,.040,.326,.218,.341)],
 'Shipper Reference':[(0,.225,.327,.355,.343)],
 'Port of Loading':[(0,.360,.294,.610,.309)],
 'Port of Discharge':[(0,.360,.326,.610,.342)],
 'Place of Receipt':[(0,.615,.294,.950,.309)],
 'Place of Delivery':[(0,.615,.326,.950,.342)],
 'Container Count':[(0,.324,.888,.420,.902)],
 'Freight & Charges':[(0,.047,.697,.250,.713)],
 'Place of Issue':[(0,.230,.913,.321,.929)],
 'Date of Issue':[(0,.170,.929,.318,.944)],
 'Shipped on Board Date':[(0,.320,.918,.474,.934)],
 'Number of Rider Pages':[(0,.790,.069,.843,.082)],
 'Gross Weight':[(0,.805,.647,.877,.661)],
 'Gross Measurement':[(0,.891,.647,.958,.661)],
 'Quantity':[(0,.290,.646,.328,.660)],
 'Container & Seal':[(0,.037,.382,.216,.449)],
 'Cargo Description':[(0,.239,.384,.740,.644)],
 'Invoice Number':[(0,.239,.421,.644,.437)],
}
MSC_RIDER_CELLS = dict(MSC_FRONT_CELLS)
MSC_RIDER_CELLS.update({
 'Container & Seal':[(1,.037,.136,.205,.310)],
 'Cargo Description':[(1,.239,.139,.699,.372)],
 'Quantity':[(0,.526,.401,.560,.415)],
 'Gross Weight':[(1,.765,.372,.852,.385)],
 'Gross Measurement':[(1,.872,.372,.950,.385)],
 'Invoice Number':[(1,.239,.272,.495,.294)],
 'Rider - Container Details':[(1,.037,.136,.694,.309)],
})
MSC_CELLS = dict(MSC_RIDER_CELLS)
MSC_FIELD_GROUPS = {
 'Halaman 1 - Identitas':['Waybill Number','Document Type','Shipper','Consignee','Notify Party','Number of Rider Pages'],
 'Halaman 1 - Kapal dan Rute':['Vessel / Voyage','Booking Number','Shipper Reference','Port of Loading','Port of Discharge','Place of Receipt','Place of Delivery'],
 'Halaman 1 - Muatan':['Container Count','Container & Seal','Quantity','Cargo Description','Invoice Number','Gross Weight','Gross Measurement'],
 'Halaman 1 - Freight dan Penerbitan':['Freight & Charges','Place of Issue','Date of Issue','Shipped on Board Date'],
 'Rider (bila tersedia)':['Rider - Container Details'],
}

def msc_layout(doc):
    """Native-text anchor checks, not filename or presence of arbitrary page two."""
    if not doc or not any('MEDITERRANEAN SHIPPING COMPANY' in line.upper() for line in doc[0].get_text().splitlines()):
        raise ValueError('Dokumen tidak dikenali sebagai format MSC yang didukung')
    if len(doc)>1:
        rider=doc[1].get_text().upper()
        if 'RIDER PAGE' in rider and 'CONTAINER NUMBERS' in rider.upper():
            return 'rider'
    return 'front'

def msc_cells_for_doc(doc):
    return MSC_RIDER_CELLS if msc_layout(doc)=='rider' else MSC_FRONT_CELLS

# The GSL sample's embedded text is corrupt; these cells describe its visual
# layout only. Extraction remains blocked until a readable text-layer PDF is used.
# v1.8.2: each selectable GSL field is mapped to one printed box / column.
# Normalized bounds (x0,y0,x1,y1). Page 2 (index 1) is blank in the
# supplied three-page samples; the attached-list form is on index 2.
# These are template-specific regions and must be recalibrated for new layouts.
# GSL page 1: 20 physical boxes supplied by the user (numbered 1–20).
# Coordinates are normalized PDF-page fractions, NOT screenshot pixels.
# Text in each printed caption is excluded from the comparison.
GSL_PAGE1_FIELDS = (
    'Shipper', 'Booking Number', 'Waybill Number', 'Consignee',
    'Forwarding Agent', 'Notify Party', 'Point and Country of Origin',
    'Remarks', 'Initial Carriage', 'Place of Receipt', 'Vessel',
    'Port of Loading', 'Port of Discharge', 'Final Destination',
    'Further Routing', 'Main - Container & Seal', 'Main - Cargo Description',
    'Main - Clauses', 'Freight Payable At', 'Place & Date of Issue',
)
GSL_CELLS = {name: [(0, *box)] for name, box in GSL_BOXES.items()}
GSL_CELLS.update({
 'Attached List - MKS & NOS/SEAL.NO':[(2,.07,.155,.258,.392)],
 'Attached List - Description of Goods':[(2,.258,.155,.680,.392)],
 'Attached List - Weight & Measurement':[(2,.680,.155,.975,.392)],
 'Attached List - CONT & SEAL':[(2,.07,.392,.975,.420)],
 "Attached List - SHIPPER'S LOAD STOWAGE & COUNT":[(2,.07,.420,.975,.505)],
 'Attached List - CLAUSES':[(2,.07,.525,.975,.720)],
})

# Only the top printed caption area is layout, even if OCR reads it differently.
# Two-line captions need a taller mask. A mask is limited to the caption band,
# not a global token blacklist (ADDRESS may legitimately occur in user data).
GSL_CAPTION_LINES = {
 'Notify Party': 2, 'Place of Receipt': 2, 'Final Destination': 2,
 'Main - Container & Seal': 1, 'Main - Cargo Description': 1,
 'Main - Clauses': 1,
}

GSL_FIELD_GROUPS = {
 'Halaman 1 - Identitas': list(GSL_PAGE1_FIELDS[:8]),
 'Halaman 1 - Rute': list(GSL_PAGE1_FIELDS[8:15]),
 'Halaman 1 - Muatan dan Penerbitan': list(GSL_PAGE1_FIELDS[15:]),
 'Attached List (halaman terakhir)': [name for name in GSL_CELLS if name.startswith('Attached List -')],
}


def profile_field_names(profile='waybill_anl'):
    if profile=='waybill_evergreen':return list(EVERGREEN_CELLS)
    if profile=='waybill_gsl':return list(GSL_CELLS)
    if profile=='waybill_one':return list(ONE_CELLS)
    if profile=='waybill_maersk':return list(MAERSK_CELLS)
    if profile=='waybill_meratus':return list(MERATUS_CELLS)
    if profile=='waybill_msc':return list(MSC_CELLS)
    return [name for name,_ in FIELDS]

def _profile_cells(profile, page=None):
    if profile in ('waybill','waybill_anl',None):
        return {name:[(0,*bounds)] for name,bounds in FIELDS}
    if profile=='waybill_evergreen':return EVERGREEN_CELLS
    if profile=='waybill_gsl':return GSL_CELLS
    if profile=='waybill_one':return ONE_CELLS
    if profile=='waybill_maersk':return maersk_cells_for_page(page) if page is not None else MAERSK_CELLS
    if profile=='waybill_meratus':return meratus_cells_for_page(page) if page is not None else MERATUS_CELLS
    if profile=='waybill_msc':return msc_cells_for_doc(page) if page is not None else MSC_CELLS
    raise ValueError('Preset SWB tidak dikenal: '+str(profile))

def _gsl_bounds(doc,page_no,name,bounds,cache):
    """Batas sel GSL halaman 1 yang disesuaikan ke garis formulir dokumen ini."""
    if page_no!=0 or name not in GSL_BOXES:return bounds
    if 0 not in cache:
        try:cache[0]=boxes_for_page(doc[0])[0]
        except Exception:cache[0]={}
    return cache[0].get(name,bounds)

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
        if profile == 'waybill_maersk':
            cells=maersk_cells_for_page(doc[0])
        elif profile == 'waybill_meratus':
            cells=meratus_cells_for_page(doc[0])
        elif profile == 'waybill_msc':
            cells=msc_cells_for_doc(doc)
        # Decoder-first: no OCR runtime is required for trusted Type3 glyphs.
        page_cache = {}
        snapped = {}
        for name,regions in cells.items():
            if name not in chosen:continue
            if profile=='waybill_gsl':
                if name.startswith('Attached List -'):
                    if len(doc)<2:
                        result[name]={'text':'','words':[],'valid':False,'reason':'Attached List tidak tersedia','source':'Type3'}
                        continue
                    regions=[(len(doc)-1,*region[1:]) for region in regions]
                words=[]
                unknown=False
                for page_no,*bounds in regions:
                    if page_no>=len(doc):
                        unknown=True;continue
                    if page_no not in page_cache:
                        try:page_cache[page_no]=recover_page_words(doc,page_no)
                        except (UnrecoverableGSLText,ValueError):page_cache[page_no]=[]
                    cell=_rect(doc[page_no],_gsl_bounds(doc,page_no,name,bounds,snapped))
                    for w in page_cache[page_no]:
                        # v1.8.30.9: sel memiliki seluruh rangkaian teks yang DIMULAI di dalamnya
                        if cell.contains(word_anchor(w)):
                            words.append(dict(w,confidence=100.0))
                # Type3 data glyphs exclude the printed template labels in the
                # supplied GSL files; never strip a valid field value by keyword.
                unknown=unknown or any('�' in w['word'] for w in words)
                # Empty optional GSL cells can be verified as empty when the
                # Type3 page was decoded successfully; do not invent values.
                empty_optional = {'Final Destination', 'Forwarding Agent',
                                  'Further Routing', 'Initial Carriage',
                                  'Place of Receipt', 'Point and Country of Origin', 'Main - Container & Seal'}
                verified_empty = (not words and not unknown and name in empty_optional
                                  and bool(page_cache.get(regions[0][0])))
                if (words or verified_empty) and not unknown:
                    result[name]={'text':' '.join(w['word'] for w in words),
                        'words':words,'valid':True,'source':'Type3', 'confidence':100.0}
                    continue
                # Never fabricate text or silently treat unreadable as equal.
                # This release intentionally has no OCR dependency for GSL.
                result[name]={'text':' '.join(w['word'] for w in words),
                    'words':words,'valid':False,'source':'Type3 parsial',
                    'reason':('Karakter Type3 belum terpetakan' if words else 'Tidak ada karakter terdekode pada kotak; perlu verifikasi')}
                continue
            words=[]
            for page_no,*bounds in regions:
                if page_no>=len(doc):continue
                page=doc[page_no]
                region=_rect(page,bounds)
                if profile in ('waybill_one','waybill_maersk','waybill_meratus','waybill_msc'):
                    if page_no not in page_cache:
                        page_cache[page_no]=page.get_text('words',sort=True)
                    source_words=page_cache[page_no]
                    # A variable number of container rows shifts the summary
                    # (N/M, N/N + totals) downward. Anchor to that row instead
                    # of hard-coding its Y coordinate from one sample.
                    if profile == 'waybill_one' and page_no==0 and name in {'Container & Seal','Quantity','Cargo Description','Gross Weight','Gross Measurement'}:
                        totals=[w[1] for w in source_words if str(w[4]).upper().rstrip(',')=='N/M' and w[0]<page.rect.width*.15 and .43*page.rect.height < w[1] < .62*page.rect.height]
                        if totals:
                            y=min(totals)
                            if name=='Container & Seal':
                                region=fitz.Rect(page.rect.width*.045, page.rect.height*.428, page.rect.width*.302, y-2)
                            elif name=='Quantity':
                                region=fitz.Rect(page.rect.width*.288, y-1, page.rect.width*.35, y+page.rect.height*.025)
                            elif name=='Cargo Description':
                                region=fitz.Rect(page.rect.width*.357, y-1, page.rect.width*.748, page.rect.height*.62)
                            elif name=='Gross Weight':
                                region=fitz.Rect(page.rect.width*.746, y-2, page.rect.width*.869, y+page.rect.height*.019)
                            else:
                                region=fitz.Rect(page.rect.width*.869, y-2, page.rect.width*.987, y+page.rect.height*.019)
                    # ONE attached-list second page has a variable-height goods
                    # description. Clauses begin at the first OCEAN FREIGHT
                    # heading, never at an assumed fixed percentage.
                    if profile == 'waybill_one' and name=='Attached List - Clauses':
                        starts=[w[1] for w in source_words if str(w[4]).upper()=='OCEAN' and w[0]<page.rect.width*.12 and w[1]>page.rect.height*.25]
                        if starts:
                            region.y0=min(starts)-1
                        else:
                            continue
                    elif profile == 'waybill_one' and name=='Attached List - Description of Goods':
                        starts=[w[1] for w in source_words if str(w[4]).upper()=='OCEAN' and w[0]<page.rect.width*.12 and w[1]>page.rect.height*.25]
                        if starts:
                            region.y1=min(starts)-3
                    for w in source_words:
                        token=str(w[4]).strip()
                        if not token or token in {'SH>','CN>','NP>'}:continue
                        wr=fitz.Rect(w[:4]); middle=(wr.tl+wr.br)*.5
                        if profile in ('waybill_maersk','waybill_meratus','waybill_msc') and (wr.height > page.rect.height*.026 or token.upper() in {'CERTIFIED', 'VERIFY', 'COPY', 'DRAFT', 'NON-NEGOTIABLE'}):
                            # Exclude oversized draft/certification watermarks, not cargo text.
                            continue
                        if region.contains(middle):
                            words.append({'word':token,'rect':wr,'page':page_no})
                else:
                    for w in page.get_text('words',clip=region,sort=True):
                        token=str(w[4]).strip()
                        if token:words.append({'word':token,'rect':fitz.Rect(w[:4]),'page':page_no})
            if profile == 'waybill_msc' and name == 'Document Type':
                words=[w for w in words if w['word'].casefold().rstrip('.') != 'no']
            if profile == 'waybill_msc' and name == 'Invoice Number':
                # The field is the actual invoice ID, not the adjacent prose.
                for i,w in enumerate(words[:-1]):
                    if w['word'].upper().rstrip('.:') == 'NO':
                        words=[words[i+1]]
                        break
            result[name]={'text':' '.join(w['word'] for w in words),'words':words}
        if profile in ('waybill_meratus','waybill_msc'):
            for field in chosen:
                result.setdefault(field, {'text':'','words':[]})
    return result

# True = tandai SELURUH isi field (perilaku v1.8.29); False = hanya kata yang berbeda.
GSL_MARK_WHOLE_FIELD = False

def _gsl_changed_hits(a,b,kind):
    """Penanda per kata untuk satu field GSL. Satu perbedaan per field tetap dipertahankan."""
    if GSL_MARK_WHOLE_FIELD or kind!='Perubahan' or not a or not b:
        return _hits(a,0,len(a),kind),_hits(b,0,len(b),kind)
    matcher=SequenceMatcher(None,[_norm(w['word']) for w in a],[_norm(w['word']) for w in b],autojunk=False)
    ia=[];ib=[]
    for op,i1,i2,j1,j2 in matcher.get_opcodes():
        if op=='equal':continue
        ia+=list(range(i1,i2));ib+=list(range(j1,j2))
    ha=[{'page':a[i]['page'],'rect':a[i]['rect'],'kind':kind} for i in ia] or _hits(a,0,len(a),kind)
    hb=[{'page':b[j]['page'],'rect':b[j]['rect'],'kind':kind} for j in ib] or _hits(b,0,len(b),kind)
    return ha,hb

def compare_waybills(reference_pdf,examined_pdf,selected=None,profile='waybill_anl'):
    cells=_profile_cells(profile)
    selected=set(selected) if selected is not None else set(cells)
    global GSL_SKIPPED_FIELDS, GSL_DIAGNOSTICS, REFERENCE_NEEDS_REVIEW, REFERENCE_EXTRACTION_DIAGNOSTICS
    GSL_SKIPPED_FIELDS = []
    GSL_DIAGNOSTICS = {}
    REFERENCE_NEEDS_REVIEW = []
    REFERENCE_EXTRACTION_DIAGNOSTICS = {}
    # The selected SWB preset describes ONLY the examined document (PDF B).
    # PDF A is independently recognised as a labelled reference or as the
    # corresponding carrier form. This preserves each carrier's field list.
    is_anl = profile in ('waybill','waybill_anl',None)
    reference_flexible = detect_flexible_pdf(reference_pdf, selected)
    # v1.8.33.2: pada profil ANL kata rujukan dibaca per kata supaya penanda hanya menutup nilai.
    ref = (extract_flexible(reference_pdf, selected, word_level=is_anl) if reference_flexible
           else extract(reference_pdf, selected, profile))
    # Allow a labelled PDF B for diagnostics/tests; carrier forms keep their own engine.
    examined_flexible = detect_flexible_pdf(examined_pdf, selected)
    exam = (extract_flexible(examined_pdf, selected, word_level=is_anl) if examined_flexible
            else extract(examined_pdf, selected, profile))
    if reference_flexible:
        REFERENCE_EXTRACTION_DIAGNOSTICS = {
            f: {'valid': bool(v.get('valid')), 'text': v.get('text',''),
                'reason':v.get('reason',''), 'source':v.get('source','')}
            for f,v in ref.items()
        }
    differences=[];locations=[]
    for name in cells:
        if name not in selected:continue
        if reference_flexible and not ref[name].get('valid',False):
            REFERENCE_NEEDS_REVIEW.append(name)
            if profile=='waybill_gsl': GSL_SKIPPED_FIELDS.append(name)
            # An absent field on the reference is unknown, not an empty value.
            continue
        if examined_flexible and not exam[name].get('valid',False):
            REFERENCE_NEEDS_REVIEW.append(name)
            if profile=='waybill_gsl': GSL_SKIPPED_FIELDS.append(name)
            continue
        if profile=='waybill_gsl':
            GSL_DIAGNOSTICS[name] = {'rujukan': {'valid': ref[name].get('valid'), 'text': ref[name].get('text',''), 'words': ref[name].get('words',[]), 'reason': ref[name].get('reason',''), 'source': ref[name].get('source','')}, 'diperiksa': {'valid': exam[name].get('valid'), 'text': exam[name].get('text',''), 'words': exam[name].get('words',[]), 'reason': exam[name].get('reason',''), 'source': exam[name].get('source','')}}
            if (ref[name].get('valid') is False or exam[name].get('valid') is False):
                GSL_SKIPPED_FIELDS.append(name)
                continue
        a=ref[name]['words'];b=exam[name]['words']
        # Flexible documents may wrap the same sentence at different positions.
        # Compare the full field without layout-induced whitespace, and never
        # turn an unknown field into a false MATCH.
        if reference_flexible or examined_flexible:
            ref_text, exam_text = ref[name]['text'], exam[name]['text']
            # ANL: bandingkan NILAI kanonik (angka, kontainer, tanggal) bila layout rujukan berbeda
            # dari formulir; hasilnya None bila tidak ada aturan -> perbandingan teks biasa.
            same = None
            if is_anl:
                ref_value = ref[name].get('semantic_text', ref_text)
                exam_value = exam[name].get('semantic_text', exam_text)
                same = fields_equal(name, ref_value, exam_value)
                if 'semantic_words' in exam[name]:
                    b, exam_text = exam[name]['semantic_words'], exam_value
                if 'semantic_words' in ref[name]:
                    a, ref_text = ref[name]['semantic_words'], ref_value
            if same is None:
                at = re.sub(r'\s+', '', ref_text).casefold()
                bt = re.sub(r'\s+', '', exam_text).casefold()
                same = (at == bt)
            if not same:
                kind = 'Perubahan' if a and b else ('Hilang' if a else 'Berlebih')
                differences.append(WaybillDifference(kind,None,None,ref_text,exam_text,
                    'Field Waybill: '+name+'; '+kind,False,name))
                hits_a,hits_b=_gsl_changed_hits(a,b,kind)
                locations.append(({'hits':hits_a},{'hits':hits_b}))
            continue
        # Page 1 GSL: compare the entire data field, not OCR word fragments.
        # A single difference also gives one correction note per physical box.
        if profile == 'waybill_gsl' and name in GSL_PAGE1_FIELDS:
            at = ' '.join(_norm(w['word']) for w in a)
            bt = ' '.join(_norm(w['word']) for w in b)
            if at != bt:
                kind = 'Perubahan' if a and b else ('Hilang' if a else 'Berlebih')
                differences.append(WaybillDifference(kind, None, None,
                    ' '.join(w['word'] for w in a), ' '.join(w['word'] for w in b),
                    'Field Waybill: ' + name + '; ' + kind, False, name))
                hits_a, hits_b = _gsl_changed_hits(a, b, kind)
                locations.append(({'hits': hits_a}, {'hits': hits_b}))
            continue
        matcher=SequenceMatcher(None,[_norm(w['word']) for w in a],[_norm(w['word']) for w in b],autojunk=False)
        for op,i1,i2,j1,j2 in matcher.get_opcodes():
            if op=='equal':continue
            kind={'replace':'Perubahan','delete':'Hilang','insert':'Berlebih'}[op]
            differences.append(WaybillDifference(kind,None,None,' '.join(w['word'] for w in a[i1:i2]),
                ' '.join(w['word'] for w in b[j1:j2]),'Field Waybill: '+name+'; '+kind + ('; OCR — verifikasi manual' if profile=='waybill_gsl' and (ref[name].get('source')=='OCR' or exam[name].get('source')=='OCR') else ''),False,name))
            locations.append(({'hits':_hits(a,i1,i2,kind)}, {'hits':_hits(b,j1,j2,kind)}))
    return differences,locations


def audit_gsl_page1(reference_path, examined_path):
    """Audit all 20 physical page-one boxes, independent of UI selection.

    Status is distinct for matched, changed, verified empty, and unreadable.
    This never upgrades unknown Type3 glyphs to a guessed character.
    """
    ref = extract(reference_path, chosen=GSL_PAGE1_FIELDS, profile='waybill_gsl')
    exam = extract(examined_path, chosen=GSL_PAGE1_FIELDS, profile='waybill_gsl')
    entries = []
    for index, name in enumerate(GSL_PAGE1_FIELDS, 1):
        a, b = ref[name], exam[name]
        if not a.get('valid') or not b.get('valid'):
            status = 'PERLU_VERIFIKASI'
        elif not a['text'].strip() and not b['text'].strip():
            status = 'KOSONG_KEDUANYA'
        elif normalize_text(a['text']) == normalize_text(b['text']):
            status = 'SAMA'
        else:
            status = 'BERBEDA'
        entries.append({
            'nomor': index, 'field': name, 'status': status,
            'rujukan': a.get('text', ''), 'diperiksa': b.get('text', ''),
            'rujukan_valid': bool(a.get('valid')),
            'diperiksa_valid': bool(b.get('valid')),
            'rujukan_alasan': a.get('reason', ''),
            'diperiksa_alasan': b.get('reason', ''),
            'koordinat_normalisasi': [list(r) for r in GSL_CELLS[name]],
        })
    return entries
