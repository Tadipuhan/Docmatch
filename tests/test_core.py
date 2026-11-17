from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from session_store import save_session,load_session,fingerprint,validate_documents
from template_manager import validate_templates,read_templates,write_templates
import pymupdf as fitz


def make_pdf(path, text='Hello DocMatch'):
    with fitz.open() as d:
        page=d.new_page();page.insert_text((45,50),text);d.save(path)


def test_session_roundtrip(tmp_path):
    a=tmp_path/'a.pdf';b=tmp_path/'b.pdf'
    make_pdf(a);make_pdf(b,'Other text')
    payload={'documents':{'reference':fingerprint(a),'examined':fingerprint(b)},
             'comparison':{'diffs':[]},'stage2':{'records':{},'visibility':{}}}
    file=tmp_path/'session.dmjson'
    save_session(file,payload)
    restored=load_session(file)
    assert restored['documents']==payload['documents']
    assert restored['schema_version']==1
    assert not list(tmp_path.glob('*.tmp'))


def test_session_rejects_changed_pdf(tmp_path):
    a=tmp_path/'a.pdf';b=tmp_path/'b.pdf'
    make_pdf(a);make_pdf(b)
    payload={'documents':{'reference':fingerprint(a),'examined':fingerprint(b)},
             'comparison':{},'stage2':{}}
    file=tmp_path/'session.dmjson';save_session(file,payload)
    make_pdf(a.with_suffix('.new.pdf'),'different')
    a.write_bytes(a.with_suffix('.new.pdf').read_bytes())
    with pytest.raises(ValueError, match='berubah'):
        load_session(file)


def test_malformed_session(tmp_path):
    file=tmp_path/'bad.dmjson';file.write_text('{"schema_version":99}',encoding='utf-8')
    with pytest.raises(ValueError): load_session(file,False)


def test_templates(tmp_path):
    dest=tmp_path/'template_aliases.json'
    tpl={'waybill_gsl':{'Notify Party':['Notify Name & Address']}}
    write_templates(dest,tpl)
    assert read_templates(dest)==tpl
    with pytest.raises(ValueError):validate_templates({'waybill_gsl':{'test':'not list'}})


def test_vector_pdf_copy_unchanged(tmp_path):
    source=tmp_path/'original.pdf';out=tmp_path/'annotated.pdf'
    make_pdf(source)
    original=source.read_bytes()
    with fitz.open(source) as pdf:
        page=pdf[0];shape=page.new_shape();shape.draw_rect(fitz.Rect(40,40,130,60));shape.finish(color=(1,0,0));shape.commit();pdf.save(out)
    assert source.read_bytes()==original
    with fitz.open(out) as d:
        assert len(d)==1 and 'Hello DocMatch' in d[0].get_text()
