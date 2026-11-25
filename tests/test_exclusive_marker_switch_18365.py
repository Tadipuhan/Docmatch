"""v1.8.36.5 exclusive match/mismatch switch and safe green numbered badges."""
from pathlib import Path
import ast
import sys
from types import SimpleNamespace

import pymupdf as fitz
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from matched_values import number_match_marks, layout_match_markers
from correction_markers import _intersects_with_clearance


def _window_method(name):
    tree=ast.parse((ROOT/'docmatch.py').read_text(encoding='utf8'))
    cls=next(obj for obj in tree.body if isinstance(obj,ast.ClassDef) and obj.name=='Window')
    fn=next(obj for obj in cls.body if isinstance(obj,ast.FunctionDef) and obj.name==name)
    namespace={'fitz':fitz}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                 str(ROOT/'docmatch.py'),'exec'),namespace)
    return namespace[name]


def test_stable_green_numbering_both_documents_and_deduplicated_fields():
    marks=[{'field':'Quantity','page':0,'rect':[100,200,150,210]},
           {'field':'Quantity','page':0,'rect':[150,200,178,210]},
           {'field':'Booking Number','page':0,'rect':[50,50,130,62]},
           {'field':'Shipper','page':0,'rect':[20,80,150,100]}]
    matches=[{'field':'Booking Number'},{'field':'Quantity'}]
    numbered=number_match_marks(marks,matches)
    assert [(x['field'],x['id']) for x in numbered]==[
        ('Quantity',2),('Quantity',2),('Booking Number',1)]
    assert 'id' not in marks[0]
    assert number_match_marks(marks,matches)==number_match_marks(marks,matches)
    assert number_match_marks(marks,[])==[]


def test_marker_near_highlight_without_hiding_text(tmp_path):
    path=tmp_path/'test.pdf'
    with fitz.open() as pdf:
        p=pdf.new_page(width=420,height=340)
        p.insert_text((70,110),'JKTG86701300',fontsize=12)
        p.insert_text((70,170),'NAGOYA TOWER 033N',fontsize=12)
        pdf.save(path)
    with fitz.open(path) as pdf:
        page=pdf[0]
        a=page.search_for('JKTG86701300')[0]
        b=page.search_for('NAGOYA TOWER 033N')[0]
        marks=[{'field':'Booking Number','id':1,'rect':a,'page':0},
               {'field':'Vessel / Voyage','id':2,'rect':b,'page':0}]
        badges=layout_match_markers(page,marks)
        assert {badge['id'] for badge in badges}=={1,2}
        for badge in badges:
            box=badge['rect']
            assert not box.intersects(a) and not box.intersects(b)
            assert 0 <= box.x0 < box.x1 <= page.rect.x1
            assert 0 <= box.y0 < box.y1 <= page.rect.y1
            for word in page.get_text('words'):
                assert not _intersects_with_clearance(box,fitz.Rect(word[:4]),0.7)
        assert not badges[0]['rect'].intersects(badges[1]['rect'])


def test_green_numbered_preview_is_exclusive_in_source():
    tree=ast.parse((ROOT/'docmatch.py').read_text(encoding='utf8'))
    paper=next(obj for obj in tree.body if isinstance(obj,ast.ClassDef) and obj.name=='Paper')
    render=next(obj for obj in paper.body if isinstance(obj,ast.FunctionDef) and obj.name=='render')
    text=ast.get_source_segment((ROOT/'docmatch.py').read_text(encoding='utf8'),render)
    assert 'if self.show_matches:' in text
    assert 'elif self.highlights:' in text
    assert 'self._draw_diff_marks(painter,scale,img)' in text
    assert 'layout_match_markers(p,page_marks)' in text
    assert "f\"#{badge['id']:02d}\"" in text


def test_export_only_one_status_and_numbered_green_pdf(tmp_path):
    source=tmp_path/'source.pdf'
    with fitz.open() as pdf:
        page=pdf.new_page(width=490,height=360)
        page.insert_text((75,100),'JKTG86701300',fontsize=11)
        page.insert_text((75,180),'WRONG SHIPPER',fontsize=11)
        pdf.save(source)
    export=_window_method('export_waybill_pdf')
    with fitz.open(source) as src:
        green=src[0].search_for('JKTG86701300')[0]
        red=src[0].search_for('WRONG SHIPPER')[0]
        viewer=SimpleNamespace(pdf=src,match_marks=[{'id':1,'field':'Booking Number','page':0,'rect':green}])
        def save(checked,filename):
            fake=SimpleNamespace(exam_view=viewer,ref_view=viewer,
                exam_marks=[{'id':1,'page':0,'rect':red,'kind':'Perubahan'}],
                ref_marks=[],diffs=[SimpleNamespace(field='Shipper')],
                stage2_visibility={},match_switch=SimpleNamespace(isChecked=lambda:checked),
                hybrid_stage2_records={},_visible_stage2_marks=lambda side:[])
            dest=tmp_path/filename
            export(fake,dest,'exam')
            with fitz.open(dest) as result:
                drawings=result[0].get_drawings()
                labels=result[0].get_text()
                return drawings, labels, len(result)
        on,txt_on,pages_on=save(True,'same.pdf')
        off,txt_off,pages_off=save(False,'different.pdf')
        colors_on={tuple(round(x,2) for x in d.get('color') or ()) for d in on}
        colors_off={tuple(round(x,2) for x in d.get('color') or ()) for d in off}
        assert (0.04,0.54,0.33) in colors_on
        assert (0.91,0.29,0.37) not in colors_on
        assert (0.91,0.29,0.37) in colors_off
        assert (0.04,0.54,0.33) not in colors_off
        assert '#01' in txt_on and '#01' not in txt_off
        assert pages_on==pages_off==1


def test_default_off_and_switch_does_not_touch_comparison_results():
    code=(ROOT/'docmatch.py').read_text(encoding='utf8')
    assert "self.match_switch=QPushButton('○  Sama: OFF')" in code
    assert "self.match_switch.toggled.connect(self.toggle_matched_values)" in code
    assert 'viewer.show_matches=bool(enabled)' in code
    assert 'number_match_marks(self.ref_match_marks, self._visible_match_records())' in code
    assert 'number_match_marks(self.exam_match_marks, self._visible_match_records())' in code
    assert 'number_match_marks(self.ref_match_marks, self.verified_matches)' in code


def test_real_pl_si_to_swb_green_numbers_and_red_shipment_exclusion(tmp_path):
    from pl_si_reference import extract_pl_si, merge_pdf, additional_claims
    from waybill_rules import compare_waybills
    from matched_values import match_marks
    si=Path('/mnt/data/SI 26YA1A.pdf')
    pl=Path('/mnt/data/PL 26YA1A.pdf')
    swb=Path('/mnt/data/SWB 26YA1A.pdf')
    if not all(x.is_file() for x in (si,pl,swb)):
        pytest.skip('Dokumen 26YA1A asli hanya tersedia saat pengujian internal')
    records,_=extract_pl_si(si,pl)
    virtual=tmp_path/'SI_PL.pdf'
    merge_pdf(si,pl,virtual)
    selected={'Shipper','Booking Number','Consignee','Notify Party',
              'Vessel / Voyage','Port of Loading','Port of Discharge',
              'Container & Seal','Quantity','Cargo Description','Gross Weight','Gross Measurement'}
    verified=[]
    diffs,_=compare_waybills(virtual,swb,selected,profile='waybill_one',
                             reference_records=records,matched_locations=verified)
    extras,_=additional_claims(swb,'waybill_one',records,matched_locations=verified)
    assert [(d.field,d.kind) for d in diffs]==[('Shipper','Perubahan')]
    assert not extras
    order=[];seen=set()
    for rec in verified:
        if rec['field'] not in seen:
            order.append(rec);seen.add(rec['field'])
    assert len(order)==14 and 'Shipper' not in seen
    for path,side in ((virtual,'ref'),(swb,'exam')):
        marks=number_match_marks(match_marks(verified,side=side),order)
        with fitz.open(path) as pdf:
            available={m['id'] for m in marks}
            displayed=set()
            for page_id,page in enumerate(pdf):
                badges=layout_match_markers(page,[m for m in marks if m['page']==page_id])
                displayed.update(b['id'] for b in badges)
            assert displayed==available
