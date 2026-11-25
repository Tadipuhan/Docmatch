"""v1.8.36.3: both inspector tabs respond to the match switch without mutating findings.

These tests run without a GUI runtime by executing the real Window methods
against small Qt-compatible fakes. Full Windows Qt smoke testing remains required.
"""
from __future__ import annotations
import ast
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from matched_values import match_marks


class _Flags:
    ItemIsEnabled=1
    ItemIsUserCheckable=2
class _Roles:
    UserRole=32
class _States:
    Checked=2
    Unchecked=0
class Qt:
    ItemFlag=_Flags
    ItemDataRole=_Roles
    CheckState=_States
class QBrush:
    def __init__(self,color):self.color=color
class QColor:
    def __init__(self,s):self.name=s
class QTreeWidgetItem:
    def __init__(self,args):
        self.title=args[0];self.value=None;self.children=[];self._flags=1
    def setData(self,col,role,data):self.value=data
    def data(self,col,role):return self.value
    def setFlags(self,flags):self._flags=flags
    def flags(self):return self._flags
    def setForeground(self,col,value):pass
    def setToolTip(self,col,value):pass
    def addChild(self,item):self.children.append(item)
    def setExpanded(self,expanded):pass
class QListWidgetItem:
    def __init__(self,label):self.label=label;self.value=None;self._flags=1;self.state=None
    def setData(self,role,data):self.value=data
    def data(self,role):return self.value
    def setFlags(self,value):self._flags=value
    def flags(self):return self._flags
    def setCheckState(self,state):self.state=state
    def checkState(self):return self.state
    def setForeground(self,brush):pass
    def setToolTip(self,text):pass
    def text(self):return self.label


def method(name):
    tree=ast.parse((ROOT/'docmatch.py').read_text(encoding='utf8'))
    window=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Window')
    func=next(x for x in window.body if isinstance(x,ast.FunctionDef) and x.name==name)
    ns=dict(Qt=Qt,QBrush=QBrush,QColor=QColor,QTreeWidgetItem=QTreeWidgetItem,
            QListWidgetItem=QListWidgetItem,match_marks=match_marks)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func],type_ignores=[])),
                 str(ROOT/'docmatch.py'),'exec'),ns)
    return ns[name]


class MockCombo:
    def __init__(self,current='Semua'):self.values=['Semua','Perubahan'];self.current=current
    def blockSignals(self,x):pass
    def clear(self):self.values=[]
    def addItems(self,items):self.values=list(items)
    def currentText(self):return self.current
    def setCurrentText(self,value):self.current=value
    def findText(self,value):return self.values.index(value) if value in self.values else -1
class MockList:
    def __init__(self):self.items=[]
    def blockSignals(self,value):pass
    def clear(self):self.items=[]
    def addTopLevelItem(self,item):self.items.append(item)
    def addItem(self,item):self.items.append(item)
    def count(self):return len(self.items)
    def item(self,index):return self.items[index]
class MockText:
    def __init__(self):self.value='';self.placeholder=''
    def setText(self,text):self.value=text
    def setPlaceholderText(self,text):self.placeholder=text
    def text(self):return self.value
class MockViewer:
    def __init__(self):self.pdf=True;self.show_matches=False;self.rendered=0;self.page=None
    def render(self):self.rendered+=1
    def goto(self,p):self.page=p


def test_verified_records_have_text_and_page_for_readonly_tabs():
    a=MockViewer();b=MockViewer()
    sample=[{'field':'Booking Number','reference_text':'JKTG86701300',
             'examined_text':'JKTG86701300',
             'ref_hits':[{'page':0,'rect':[10,20,100,30]}],
             'exam_hits':[{'page':0,'rect':[12,22,102,32]}]},
            {'field':'Shipper','reference_text':'A','examined_text':'B',
             'ref_hits':[{'page':0,'rect':[1,1,2,2]}],
             'exam_hits':[{'page':0,'rect':[1,1,2,2]}]}]
    fake=SimpleNamespace(diffs=[SimpleNamespace(field='Shipper')],matched_fields=set(),
        verified_matches=[],ref_match_marks=[],exam_match_marks=[],
        ref_view=a,exam_view=b,match_switch=SimpleNamespace(isChecked=lambda:True))
    method('_set_verified_matches')(fake,sample)
    assert fake.matched_fields=={'Booking Number'}
    assert fake.verified_matches==[{'field':'Booking Number','reference_text':'JKTG86701300',
                                   'examined_text':'JKTG86701300','ref_page':0,'exam_page':0}]
    assert a.show_matches and b.show_matches
    assert len(a.match_marks)==len(b.match_marks)==1


def test_tahap_1_shows_matches_without_editable_checkboxes():
    record={'field':'Booking Number','reference_text':'JKTG86701300',
            'examined_text':'JKTG86701300','ref_page':0,'exam_page':0}
    fake=SimpleNamespace(list=MockList(),filter=MockCombo('Perubahan'),detail=MockText(),
                         has_compared=True,verified_matches=[record],diffs=[],hybrid_stage2_records={})
    fake._visible_match_records=lambda:method('_visible_match_records')(fake)
    method('_populate_matched_results')(fake)
    assert len(fake.list.items)==1
    parent=fake.list.items[0]
    assert parent.value==('matched','Booking Number')
    assert not parent._flags & Qt.ItemFlag.ItemIsUserCheckable
    assert len(parent.children)==1 and 'JKTG86701300' in parent.children[0].title
    assert fake.filter.values==['Semua','Sama']


def test_tahap_2_toggle_shows_only_matched_when_on_and_diff_when_off():
    record={'field':'Booking Number','reference_text':'JKTG86701300',
            'examined_text':'JKTG86701300','ref_page':0,'exam_page':0}
    fake=SimpleNamespace(export_annotation_list=MockList(),export_annotation_search=MockText(),
         stage2_info=MockText(),has_compared=True,verified_matches=[record],
         diffs=[SimpleNamespace(field='Shipper')],hybrid_stage2_records={},
         stage2_annotations={'Shipper':{'A':{}}},stage2_visibility={'Shipper':False})
    fake._visible_match_records=lambda:method('_visible_match_records')(fake)
    fake._filter_export_annotations=lambda x:None
    fake.match_switch=SimpleNamespace(isChecked=lambda:True)
    method('_refresh_export_annotations')(fake)
    assert len(fake.export_annotation_list.items)==1
    item=fake.export_annotation_list.items[0]
    assert item.value==('matched','Booking Number')
    assert not item._flags & Qt.ItemFlag.ItemIsUserCheckable
    assert fake.stage2_visibility['Shipper'] is False
    fake.match_switch=SimpleNamespace(isChecked=lambda:False)
    method('_refresh_export_annotations')(fake)
    assert len(fake.export_annotation_list.items)==1
    item=fake.export_annotation_list.items[0]
    assert item.value==('annotation','Shipper')
    assert item._flags & Qt.ItemFlag.ItemIsUserCheckable
    assert item.state==Qt.CheckState.Unchecked


def test_switch_refreshes_both_result_tabs_and_preserves_differences():
    result=[]
    viewer_a=MockViewer();viewer_b=MockViewer()
    filter=MockCombo('Perubahan')
    fake=SimpleNamespace(match_switch=SimpleNamespace(setText=lambda v:result.append(v)),
        ref_view=viewer_a,exam_view=viewer_b,has_compared=True,
        filter=filter,_difference_filter='Semua',diffs=[SimpleNamespace(field='Shipper',apply=True)],
        status=MockText(),detail=MockText(),_visible_match_records=lambda:[{'field':'Booking Number'}],
        populate=lambda:result.append('tahap1'),
        _refresh_export_annotations=lambda:result.append('tahap2'),
        _log_event=lambda key,detail:result.append(key))
    method('toggle_matched_values')(fake,True)
    assert fake._difference_filter=='Perubahan'
    assert result.count('tahap1')==result.count('tahap2')==1
    method('toggle_matched_values')(fake,False)
    assert filter.currentText()=='Perubahan'
    assert result.count('tahap1')==result.count('tahap2')==2
    assert fake.diffs[0].apply is True
    assert viewer_a.rendered==viewer_b.rendered==2


def test_new_comparison_and_restore_refresh_readonly_lists():
    text=(ROOT/'docmatch.py').read_text(encoding='utf8')
    assert "'verified_matches':self.verified_matches" in text
    assert "self.verified_matches=list(data.get('verified_matches', []))" in text
    assert "if self.match_switch.isChecked():\n            self.populate()" in text
    assert 'self._refresh_export_annotations()' in text
