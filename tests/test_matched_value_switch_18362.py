"""v1.8.36.2: verified equal-value overlays stay independent of corrections."""
from pathlib import Path
import ast
import copy
import sys
from types import SimpleNamespace

import pymupdf as fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import waybill_rules as wb
from pl_si_reference import extract_pl_si, merge_pdf, additional_claims
from matched_values import match_marks, compare_equal_paragraphs

SI = Path('/mnt/data/SI 26YA1A.pdf')
PL = Path('/mnt/data/PL 26YA1A.pdf')
SWB = Path('/mnt/data/SWB 26YA1A.pdf')


@pytest.fixture
def reference(tmp_path):
    if not all(file.is_file() for file in (SI, PL, SWB)):
        pytest.skip('Real sample PDFs not installed with distributable source')
    records, meta = extract_pl_si(SI, PL)
    virtual = tmp_path/'SI_PL.pdf'
    merge_pdf(SI, PL, virtual)
    return records, virtual


def test_verified_same_fields_have_independent_locations_from_real_pl_si(reference):
    records, virtual = reference
    fields = {'Shipper','Booking Number','Consignee','Notify Party','Vessel / Voyage',
              'Port of Loading','Port of Discharge','Container & Seal',
              'Quantity','Cargo Description','Gross Weight','Gross Measurement'}
    equal = []
    differences, locations = wb.compare_waybills(
        virtual, SWB, fields, profile='waybill_one', reference_records=records,
        matched_locations=equal)
    assert [d.field for d in differences] == ['Shipper']
    assert len(locations) == 1
    names = {record['field'] for record in equal}
    assert names == fields - {'Shipper'}
    left, right = match_marks(equal, side='ref'), match_marks(equal, side='exam')
    assert left and right and all(m['kind'] == 'Sama' for m in left + right)
    with fitz.open(virtual) as ref_pdf, fitz.open(SWB) as swb_pdf:
        assert any(m['field'] == 'Container & Seal' and m['page'] == 1 for m in left)
        for m in left:
            assert ref_pdf[m['page']].rect.intersects(m['rect'])
        for m in right:
            assert swb_pdf[m['page']].rect.intersects(m['rect'])


def test_cargo_green_excludes_unverified_extra_words(reference):
    # ONE includes "NET WEIGHT" and misplaced SH> continuation near goods.
    # Cargo equivalence must never paint these unrelated phrases green.
    records, virtual = reference
    equal=[]
    differences,_=wb.compare_waybills(virtual,SWB,{'Cargo Description'},
        profile='waybill_one',reference_records=records, matched_locations=equal)
    assert not differences and [item['field'] for item in equal]==['Cargo Description']
    with fitz.open(SWB) as swb:
        annotated=[swb[hit['page']].get_textbox(hit['rect']).strip().upper()
                   for hit in equal[0]['exam_hits']]
    assert not any('KAB.' in word or 'NET' in word or 'KARAWANG' in word
                   or 'WEIGHT' in word for word in annotated)
    assert any('BRIDGESTONE' in word for word in annotated)


def test_changed_or_unreadable_values_never_get_green(reference):
    records, virtual = reference
    changed = copy.deepcopy(records)
    changed['Booking Number']['text'] = 'WRONG-BOOKING'
    changed['Container & Seal'] = {'text':'', 'words':[], 'valid':False}
    equal = []
    issues, _ = wb.compare_waybills(
        virtual, SWB, {'Booking Number','Container & Seal','Gross Measurement'},
        profile='waybill_one', reference_records=changed, matched_locations=equal)
    assert 'Booking Number' in {d.field for d in issues}
    assert 'Container & Seal' in wb.REFERENCE_NEEDS_REVIEW
    assert [record['field'] for record in equal] == ['Gross Measurement']


def test_regular_same_profile_backwards_compatible_with_optional_collector():
    if not SWB.is_file(): pytest.skip('SWB sample missing')
    chosen={'Booking Number','Port of Loading','Vessel / Voyage'}
    baseline = wb.compare_waybills(SWB, SWB, chosen, profile='waybill_one')
    equal=[]
    actual = wb.compare_waybills(SWB, SWB, chosen, profile='waybill_one',matched_locations=equal)
    assert baseline == actual and actual[0] == []
    assert {i['field'] for i in equal} == chosen


def test_extra_pl_si_fields_green_only_when_verified_match(reference):
    records, virtual = reference
    equal=[]
    differences, review = additional_claims(SWB, 'waybill_one', records, matched_locations=equal)
    assert differences == [] and review == []
    assert {e['field'] for e in equal} == {'Invoice Number','HS Code','Net Weight'}
    assert any(hit['page'] == 1 for item in equal if item['field'] == 'Invoice Number'
               for hit in item['ref_hits'])
    altered = copy.deepcopy(records)
    altered['Invoice Number']['text']='26YA1B'
    equal=[]
    changed, missing = additional_claims(SWB,'waybill_one',altered,matched_locations=equal)
    assert not missing and [d.field for d,_ in changed]==['Invoice Number']
    assert 'Invoice Number' not in {x['field'] for x in equal}


def test_empty_and_bad_coordinates_never_green():
    equal=[{'field':'x','ref_hits':[{'page':0,'rect':[1,1,3,3]},
                                    {'page':0,'rect':[1,1,3,3]},
                                    {'page':0,'rect':[4,4,4,8]}],
            'exam_hits':[{'page':0,'rect':[2,2,3,4]}]}]
    assert len(match_marks(equal,side='ref')) == 1
    assert len(match_marks(equal,side='exam')) == 1


def test_generic_mode_only_unique_identical_pdf_paragraphs(tmp_path):
    sample = 'PT. BRIDGESTONE TIRE INDONESIA'
    source = tmp_path/'A.pdf'
    dest = tmp_path/'B.pdf'
    for name, text in [(source,sample),(dest,sample)]:
        with fitz.open() as pdf:
            page=pdf.new_page()
            page.insert_text((40,80),text)
            pdf.save(name)
    matched = compare_equal_paragraphs(source,dest,[sample],[sample],{0})
    assert len(matched)==1
    assert matched[0]['ref_hits'] and matched[0]['exam_hits']
    assert compare_equal_paragraphs(source,dest,[sample],['TOTALLY DIFFERENT ADDRESS'],{0})==[]
    assert compare_equal_paragraphs(source,dest,[sample],[sample],set())==[]


def _window_method(name):
    source = (ROOT/'docmatch.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    window = next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Window')
    func = next(x for x in window.body if isinstance(x,ast.FunctionDef) and x.name==name)
    namespace={'fitz':fitz}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func],type_ignores=[])),str(ROOT/'docmatch.py'),'exec'),namespace)
    return namespace[name]


def test_checkable_switch_repaints_both_pdf_panels_without_new_comparison():
    method=_window_method('toggle_matched_values')
    class Viewer:
        def __init__(self):
            self.pdf=True
            self.show_matches=False
            self.render_count=0
        def render(self):
            self.render_count+=1
    fake=SimpleNamespace(match_switch=SimpleNamespace(setText=lambda v:None),
        ref_view=Viewer(),exam_view=Viewer(),has_compared=False)
    method(fake,True)
    assert fake.ref_view.show_matches and fake.exam_view.show_matches
    assert fake.ref_view.render_count==fake.exam_view.render_count==1
    method(fake,False)
    assert not fake.ref_view.show_matches and not fake.exam_view.show_matches
    code = (ROOT/'docmatch.py').read_text(encoding='utf8')
    assert "self.match_switch.setCheckable(True)" in code
    assert 'self.match_switch.toggled.connect(self.toggle_matched_values)' in code
    assert 'matchedSwitch:checked' in code


def test_export_waybill_copy_includes_green_only_when_switch_on(tmp_path):
    if not SWB.is_file():pytest.skip('SWB fixture missing')
    export = _window_method('export_waybill_pdf')
    with fitz.open(SWB) as src:
        viewer=SimpleNamespace(pdf=src,match_marks=[
            {'field':'Booking Number','page':0,'rect':fitz.Rect(400,72,480,88)}],
            hidden_stage2_fields=set())
        def execute(checked, name):
            fake=SimpleNamespace(exam_view=viewer,ref_view=viewer,exam_marks=[],ref_marks=[],
                diffs=[],match_switch=SimpleNamespace(isChecked=lambda:checked),
                _visible_stage2_marks=lambda side:[],hybrid_stage2_records={})
            dest=tmp_path/name
            export(fake,dest,'exam')
            with fitz.open(dest) as pdf:
                return len(pdf[0].get_drawings()),len(pdf)
        with_green=execute(True,'on.pdf')
        no_green=execute(False,'off.pdf')
        assert with_green[0] > no_green[0]
        assert with_green[1]==no_green[1]==len(src)


def test_build_contains_match_locator_and_session_restores_switch():
    build=(ROOT/'build_portable.bat').read_text(encoding='utf8')
    source=(ROOT/'docmatch.py').read_text(encoding='utf8')
    assert '--hidden-import matched_values' in build
    assert "'ref_match_marks':self._marks_for_json(self.ref_match_marks)" in source
    assert "'show_matches':self.match_switch.isChecked()" in source
    assert "view.get('show_matches',False)" in source
