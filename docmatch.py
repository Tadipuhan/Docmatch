"""DocMatch v0.4: local desktop visual document comparison."""
from __future__ import annotations
import sys, tempfile, shutil, json, difflib, re
from pathlib import Path
from dataclasses import asdict
import pymupdf as fitz
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QFont, QTextCursor, QTextCharFormat, QBrush
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QFileDialog,QSplitter,QScrollArea,QListWidget,QListWidgetItem,QMessageBox,QComboBox,QFrame,QCheckBox,QDialog,QDialogButtonBox,QTextEdit,QStackedWidget,QTreeWidget,QTreeWidgetItem)
from legacy_v01 import read_blocks, compare, corrected_blocks, save_docx, libreoffice_convert
from rules import parse_embedded, resolve_scope, selective_compare
from editor import CorrectionEditor, save_annotated_docx
from waybill_rules import FIELDS, compare_waybills

RED='#850D1C'; DARK='#20232A'; BG='#F3F4F6'; GREEN='#D5F3DC'
# Supersampling improves PDF readability without changing the displayed page dimensions.
RENDER_QUALITY=2.0
HIGHLIGHT_ALPHA=65  # 0 = transparent; 255 = opaque


def make_preview(path:Path, tmp:Path)->Path:
    if path.suffix.lower()=='.pdf': return path
    if path.suffix.lower()=='.doc': path=libreoffice_convert(path,'docx',tmp)
    return libreoffice_convert(path,'pdf',tmp)

def fragments(text:str):
    # Shorter exact fragments work across PDF line wraps and text runs.
    words=re.findall(r'\w+(?:[.,]\w+)*',text,flags=re.UNICODE)
    if not words: return []
    return [' '.join(words[i:i+min(5,len(words))]) for i in range(0,min(len(words),15),5)]

class Paper(QWidget):
    def __init__(self,title):
        super().__init__(); self.pdf=None; self.page=0; self.zoom=1.15; self.marks=[]; self.title=title; self.highlights=True
        lay=QVBoxLayout(self); lay.setContentsMargins(8,8,8,8)
        bar=QHBoxLayout(); self.heading=QLabel(title); self.heading.setStyleSheet('font-weight:700')
        bar.addWidget(self.heading); bar.addStretch()
        self.prev=QPushButton('‹');self.next=QPushButton('›');self.counter=QLabel('0 / 0')
        self.minus=QPushButton('−');self.plus=QPushButton('+');self.toggle=QCheckBox('Stabilo');self.toggle.setChecked(True)
        for w in (self.prev,self.counter,self.next,self.minus,self.plus,self.toggle):bar.addWidget(w)
        lay.addLayout(bar)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(False);self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        self.canvas=QLabel('Pilih dokumen lalu klik Bandingkan');self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet('background:white; color:#6B7280;');self.canvas.setMinimumSize(240,320)
        self.scroll.setWidget(self.canvas);lay.addWidget(self.scroll,1)
        self.prev.clicked.connect(lambda:self.goto(self.page-1));self.next.clicked.connect(lambda:self.goto(self.page+1))
        self.plus.clicked.connect(lambda:self.set_zoom(self.zoom+.15));self.minus.clicked.connect(lambda:self.set_zoom(self.zoom-.15))
        self.toggle.toggled.connect(self.set_highlights)
    def set_highlights(self,enabled):self.highlights=enabled;self.render()
    def set_zoom(self,z):self.zoom=max(.6,min(2.3,z));self.render()
    def load(self,path,marks):
        if self.pdf:self.pdf.close()
        self.pdf=fitz.open(path);self.marks=marks;self.page=0;self.render()
    def goto(self,page):
        if self.pdf and 0<=page<len(self.pdf):self.page=page;self.render()
    def render(self):
        if not self.pdf:return
        p=self.pdf[self.page]
        # Render at 2x the visible resolution, then let Qt downsample smoothly.
        scale=self.zoom*RENDER_QUALITY
        pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
        img=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
        if self.highlights:
            painter=QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
            seen_markers=set()
            for m in self.marks:
                if m['page']!=self.page:continue
                rect=m['rect']*fitz.Matrix(scale,scale)
                # Semi-transparent highlighter: original black text remains visible.
                base=QColor({'Perubahan':'#E84A5F','Hilang':'#F5B942','Berlebih':'#3899E8'}.get(m.get('kind'),'#E84A5F'))
                fill=QColor(base);fill.setAlpha(HIGHLIGHT_ALPHA)
                painter.fillRect(QRectF(rect.x0,rect.y0,rect.width,rect.height),fill)
                outline=QColor(base);outline.setAlpha(155)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(outline,max(1,scale*.65)))
                painter.drawRect(QRectF(rect.x0,rect.y0,rect.width,rect.height))
                # One numbered marker per finding per page, despite multiple highlighted tokens.
                marker_key=(m['id'],m['page'])
                if marker_key in seen_markers:continue
                seen_markers.add(marker_key)
                diameter=15*scale
                x=max(2*scale,min(img.width()-diameter-2*scale,rect.x1-diameter/2))
                y=rect.y0-diameter-4*scale
                if y<0:y=min(img.height()-diameter,rect.y1+3*scale)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor({'Perubahan':'#B00020','Hilang':'#A56A00','Berlebih':'#1765A9'}.get(m.get('kind'),'#B00020')))
                painter.drawEllipse(int(x),int(y),int(diameter),int(diameter))
                painter.setPen(QColor('white'))
                painter.setFont(QFont('Arial',max(8,int(8*scale)),QFont.Weight.Bold))
                painter.drawText(int(x),int(y),int(diameter),int(diameter),Qt.AlignmentFlag.AlignCenter,str(m['id']))
            painter.end()
        result=QPixmap.fromImage(img)
        result.setDevicePixelRatio(RENDER_QUALITY)
        self.canvas.setPixmap(result)
        self.canvas.resize(result.deviceIndependentSize().toSize())
        self.counter.setText(f'{self.page+1} / {len(self.pdf)}  ·  {int(self.zoom*100)}%')


def locate(pdf_path:Path,diffs,side:str):
    marks=[]; pages={}; misses=[]
    with fitz.open(pdf_path) as pdf:
        for n,d in enumerate(diffs,1):
            text=d.examined_text if side=='exam' else d.reference_text
            if not text:continue
            # Prefer changed tokens, then fallback to a fragment of the paragraph.
            targets=[]
            if d.kind=='Perubahan':
                a=re.findall(r'\w+(?:[.,]\w+)*',d.examined_text);b=re.findall(r'\w+(?:[.,]\w+)*',d.reference_text)
                op=difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()
                for tag,i,j,k,l in op:
                    if tag!='equal':targets.extend([' '.join((a[i:j] if side=='exam' else b[k:l]))])
            targets=[t for t in targets if len(t.strip())>=2]+fragments(text)
            found=False
            for page_no,page in enumerate(pdf):
                for target in targets:
                    boxes=page.search_for(target)
                    if boxes:
                        rect=boxes[0];marks.append({'id':n,'page':page_no,'rect':rect,'side':side})
                        pages[n]=page_no;found=True;break
                if found:break
            if not found:misses.append(n)
    return marks,pages,misses

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('DocMatch v0.8 — Step Wizard (Offline)');self.resize(1100,740)
        self.tmp=tempfile.TemporaryDirectory(prefix='docmatch_v03_');self.work=Path(self.tmp.name)
        self.ref_path=None;self.exam_path=None;self.reference=[];self.examined=[];self.diffs=[];self.ref_pages={};self.exam_pages={};self.checks=[];self.scope=set();self.uncertain=[];self.mode="hybrid";self.rule_groups={};self.reference_raw=[];self.waybill_fields={name for name,_ in FIELDS};self.waybill_mode=False
        root=QWidget();self.setCentralWidget(root);main=QVBoxLayout(root);main.setContentsMargins(14,12,14,12)
        header=QHBoxLayout();brand=QLabel('▣  DocMatch');brand.setStyleSheet(f'font-size:24px;font-weight:800;color:{RED}')
        header.addWidget(brand);header.addWidget(QLabel('Pembanding & Koreksi Dokumen  •  100% Offline'));header.addStretch();main.addLayout(header)
        # Step Wizard ribbon: only this top area changes; viewers and comparison engine remain intact.
        self.wizard_steps=[]
        stepbar=QHBoxLayout();stepbar.setSpacing(7)
        for index,label in enumerate(('1  Pilih Dokumen','2  Atur Parameter','3  Perbandingan','4  Hasil & Ekspor')):
            btn=QPushButton(label);btn.setObjectName('wizardStep')
            btn.clicked.connect(lambda checked=False, i=index:self.show_step(i))
            stepbar.addWidget(btn,1);self.wizard_steps.append(btn)
        main.addLayout(stepbar)
        self.wizard_stack=QStackedWidget();main.addWidget(self.wizard_stack)
        # Step 1: document sources
        step1=QWidget();step1_layout=QHBoxLayout(step1);step1_layout.setContentsMargins(2,7,2,7)
        self.ref_btn=QPushButton('Pilih Dokumen Rujukan');self.exam_btn=QPushButton('Pilih Dokumen Diperiksa')
        self.ref_btn.clicked.connect(lambda:self.pick('ref'));self.exam_btn.clicked.connect(lambda:self.pick('exam'))
        step1_layout.addWidget(self.ref_btn,1);step1_layout.addWidget(self.exam_btn,1)
        next1=QPushButton('Atur Parameter  →');next1.clicked.connect(lambda:self.show_step(1));step1_layout.addWidget(next1)
        self.wizard_stack.addWidget(step1)
        # Step 2: comparison scope
        step2=QWidget();rules_bar=QHBoxLayout(step2);rules_bar.setContentsMargins(2,7,2,7)
        rules_bar.addWidget(QLabel('Mode parameter:'))
        self.rule_mode=QComboBox();self.rule_mode.addItem('Gabungkan tag + pilihan aplikasi','hybrid');self.rule_mode.addItem('Tag dokumen saja','embedded');self.rule_mode.addItem('Pilihan aplikasi saja','visual');self.rule_mode.addItem('Waybill (preset field)','waybill')
        rules_bar.addWidget(self.rule_mode,1)
        self.scope_btn=QPushButton('Pilih Paragraf Rujukan…');self.scope_btn.clicked.connect(self.choose_scope);rules_bar.addWidget(self.scope_btn)
        self.waybill_btn=QPushButton('Atur Field Waybill…');self.waybill_btn.clicked.connect(self.choose_waybill);rules_bar.addWidget(self.waybill_btn)
        self.all_scope=QCheckBox('Periksa seluruh dokumen');rules_bar.addWidget(self.all_scope)
        next2=QPushButton('Lanjutkan  →');next2.clicked.connect(lambda:self.show_step(2));rules_bar.addWidget(next2)
        self.wizard_stack.addWidget(step2)
        # Step 3: run comparison
        step3=QWidget();step3_layout=QHBoxLayout(step3);step3_layout.setContentsMargins(2,7,2,7)
        step3_layout.addWidget(QLabel('Periksa dokumen sesuai parameter yang dipilih.'))
        step3_layout.addStretch()
        self.run_btn=QPushButton('⌕  Bandingkan Dokumen');self.run_btn.setObjectName('primary')
        self.run_btn.clicked.connect(self.run);step3_layout.addWidget(self.run_btn)
        next3=QPushButton('Hasil & Ekspor  →');next3.clicked.connect(lambda:self.show_step(3));step3_layout.addWidget(next3)
        self.wizard_stack.addWidget(step3)
        # Step 4: result actions remain in the existing right-hand inspector.
        step4=QWidget();step4_layout=QHBoxLayout(step4);step4_layout.setContentsMargins(2,7,2,7)
        step4_layout.addWidget(QLabel('Tinjau daftar ketidaksesuaian di kanan, lalu gunakan tombol ekspor pada panel tersebut.'))
        step4_layout.addStretch()
        back4=QPushButton('←  Perbandingan');back4.clicked.connect(lambda:self.show_step(2));step4_layout.addWidget(back4)
        self.wizard_stack.addWidget(step4)
        self.rule_mode.currentIndexChanged.connect(self.mode_changed)
        self.mode_changed()
        self.show_step(0)
        split=QSplitter(Qt.Orientation.Horizontal);self.ref_view=Paper('DOKUMEN RUJUKAN');self.exam_view=Paper('DOKUMEN DIPERIKSA')
        split.addWidget(self.ref_view);split.addWidget(self.exam_view)
        side=QWidget();side.setMinimumWidth(320);side.setMaximumWidth(440);s=QVBoxLayout(side)
        heading=QLabel('Daftar Ketidaksesuaian');heading.setStyleSheet('font-size:17px;font-weight:700');s.addWidget(heading)
        self.filter=QComboBox();self.filter.addItems(['Semua','Perubahan']);self.filter.currentTextChanged.connect(self.populate);s.addWidget(self.filter)
        self.list=QTreeWidget();self.list.setHeaderHidden(True);self.list.itemClicked.connect(self.navigate_tree);s.addWidget(self.list,1)
        self.detail=QLabel('Pilih ketidaksesuaian untuk melihat detail.');self.detail.setWordWrap(True);self.detail.setMinimumHeight(90);s.addWidget(self.detail)
        self.editor_btn=QPushButton('✎  Edit Hasil Koreksi');self.editor_btn.clicked.connect(self.open_editor);s.addWidget(self.editor_btn)
        self.editor_text=None;self.editor_initial=None;self.editor_source=None
        self.apply_btn=QPushButton('Ekspor Koreksi Terpilih (DOCX)');self.apply_btn.setObjectName('primary');self.apply_btn.clicked.connect(self.export_docx)
        self.pdf_btn=QPushButton('Ekspor Koreksi (PDF)');self.pdf_btn.clicked.connect(self.export_pdf)
        self.report_btn=QPushButton('Ekspor Laporan (JSON)');self.report_btn.clicked.connect(self.export_report)
        for b in (self.apply_btn,self.pdf_btn,self.report_btn):s.addWidget(b)
        split.addWidget(side)
        # Allow all three panels to shrink; preserve independent PDF scrolling.
        for viewer in (self.ref_view, self.exam_view):
            viewer.setMinimumWidth(0)
            viewer.scroll.setMinimumWidth(0)
            viewer.canvas.setMinimumWidth(240)
        side.setMinimumWidth(320)
        split.setChildrenCollapsible(False)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 5)
        split.setStretchFactor(2, 3)
        main.addWidget(split,1)
        from PySide6.QtWidgets import QApplication
        available=QApplication.primaryScreen().availableGeometry()
        width=min(1600, max(900, int(available.width()*0.98)))
        height=min(980, max(600, int(available.height()*0.94)))
        self.resize(min(width,available.width()),min(height,available.height()))
        self.move(available.x()+max(0,(available.width()-self.width())//2),
                  available.y()+max(0,(available.height()-self.height())//2))
        split.setSizes([530,530,380])
        self.status=QLabel('v0.7 · Seleksi paragraf + tag DOCMATCH · Render PDF 2× lebih tajam · Stabilo transparan dapat diaktifkan/nonaktifkan · Seluruh proses offline.')
        main.addWidget(self.status)
        self.setStyleSheet(f'''QMainWindow,QWidget{{background:{BG};color:{DARK};font-family:Segoe UI,Arial;font-size:12px}}
          QPushButton{{background:white;border:1px solid #D8DADF;border-radius:7px;padding:10px 13px}}
          QPushButton:hover{{border-color:{RED}}} QPushButton#primary{{background:{RED};color:white;border:0;font-weight:700}}
          QScrollArea{{border:1px solid #E0E2E6;background:#E8EAEE}} QListWidget,QComboBox{{background:white;border:1px solid #D8DADF;border-radius:6px;padding:7px}}
          QListWidget::item{{padding:8px;border-bottom:1px solid #EEEEEE}} QListWidget::item:selected{{background:#F6DCE0;color:#242424}}''')
    def show_step(self,index):
        self.wizard_stack.setCurrentIndex(index)
        for i,button in enumerate(self.wizard_steps):
            button.setProperty('activeStep',i==index)
            button.setStyleSheet(
                'background:#850D1C;color:white;border:1px solid #850D1C;font-weight:700;' if i==index
                else 'background:white;color:#333;border:1px solid #D8DADF;font-weight:600;'
            )

    def pick(self,side):
        name,_=QFileDialog.getOpenFileName(self,'Pilih dokumen','','Dokumen (*.docx *.pdf *.doc)')
        if not name:return
        p=Path(name)
        if side=='ref':self.ref_path=p;self.ref_btn.setText('Rujukan: '+p.name)
        else:self.exam_path=p;self.exam_btn.setText('Diperiksa: '+p.name)
    def mode_changed(self,*args):
        is_waybill=self.rule_mode.currentData()=='waybill'
        self.scope_btn.setEnabled(not is_waybill)
        self.waybill_btn.setEnabled(is_waybill)
        self.all_scope.setEnabled(not is_waybill)

    def choose_waybill(self):
        dlg=QDialog(self);dlg.setWindowTitle('Parameter Waybill');dlg.resize(540,600)
        layout=QVBoxLayout(dlg)
        layout.addWidget(QLabel('Pilih field yang akan dibandingkan. Preset untuk layout ANL Waybill.'))
        items=QListWidget()
        for name,_ in FIELDS:
            item=QListWidgetItem(name)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in self.waybill_fields else Qt.CheckState.Unchecked)
            items.addItem(item)
        controls=QHBoxLayout()
        select_all=QPushButton('Pilih Semua')
        clear_all=QPushButton('Hapus Semua')
        controls.addWidget(select_all);controls.addWidget(clear_all);controls.addStretch()
        layout.addLayout(controls)
        layout.addWidget(items)
        def set_all(state):
            for i in range(items.count()):
                items.item(i).setCheckState(state)
        select_all.clicked.connect(lambda:set_all(Qt.CheckState.Checked))
        clear_all.clicked.connect(lambda:set_all(Qt.CheckState.Unchecked))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        def accept_selection():
            if not any(items.item(i).checkState()==Qt.CheckState.Checked for i in range(items.count())):
                QMessageBox.warning(dlg,'Parameter kosong','Pilih minimal satu field Waybill sebelum melanjutkan.')
                return
            dlg.accept()
        buttons.accepted.connect(accept_selection)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec()==QDialog.DialogCode.Accepted:
            self.waybill_fields={items.item(i).text() for i in range(items.count()) if items.item(i).checkState()==Qt.CheckState.Checked}
            self.waybill_btn.setText(f'Field Waybill: {len(self.waybill_fields)}')

    def choose_scope(self):
        if not self.ref_path:
            QMessageBox.warning(self,'Pilih rujukan','Pilih dokumen rujukan terlebih dahulu.');return
        try:
            (self.work/'rules').mkdir(exist_ok=True)
            raw,_=read_blocks(self.ref_path,self.work/'rules')
            parsed=parse_embedded(raw)
        except Exception as e:
            QMessageBox.critical(self,'Gagal membaca aturan',str(e));return
        dlg=QDialog(self);dlg.setWindowTitle('Pilih Paragraf Rujukan');dlg.resize(680,520)
        layout=QVBoxLayout(dlg);layout.addWidget(QLabel('Centang paragraf yang ingin diperiksa. Tag DOCMATCH tidak termasuk konten.'))
        items=QListWidget();layout.addWidget(items)
        for i,block in enumerate(parsed.blocks):
            item=QListWidgetItem(f'Paragraf {i+1}: {block[:180]}');item.setToolTip(block)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if i in self.scope else Qt.CheckState.Unchecked)
            items.addItem(item)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept);buttons.rejected.connect(dlg.reject);layout.addWidget(buttons)
        if dlg.exec()==QDialog.DialogCode.Accepted:
            self.scope={i for i in range(items.count()) if items.item(i).checkState()==Qt.CheckState.Checked}
            self.scope_btn.setText(f'Paragraf dipilih: {len(self.scope)}')

    def run(self):
        self.editor_text=None;self.editor_initial=None;self.editor_source=None
        if not self.ref_path or not self.exam_path:QMessageBox.warning(self,'Berkas belum lengkap','Pilih kedua dokumen.');return
        try:
            self.waybill_mode=self.rule_mode.currentData()=='waybill'
            if self.waybill_mode:
                if not self.waybill_fields:raise ValueError('Pilih minimal satu field Waybill.')
                a=self.work/'ref';b=self.work/'exam';a.mkdir(exist_ok=True);b.mkdir(exist_ok=True)
                refpdf=make_preview(self.ref_path,a);exampdf=make_preview(self.exam_path,b)
                self.diffs,locations=compare_waybills(refpdf,exampdf,self.waybill_fields)
                self.reference=[];self.examined=[];self.active_scope=set();self.uncertain=[];self.mode='waybill'
                self.ref_marks=[];self.exam_marks=[];self.ref_pages={};self.exam_pages={}
                for i,(ref_loc,exam_loc) in enumerate(locations,1):
                    for loc,marks,pages,side in ((ref_loc,self.ref_marks,self.ref_pages,'ref'),(exam_loc,self.exam_marks,self.exam_pages,'exam')):
                        for hit in loc.get('hits',[]):
                            marks.append({'id':i,'page':hit['page'],'rect':hit['rect'],'side':side,'kind':hit['kind']})
                        if loc.get('hits'):
                            pages[i]=loc['hits'][0]['page']
                self.sort_differences()
                self.ref_view.load(refpdf,self.ref_marks);self.exam_view.load(exampdf,self.exam_marks)
                self.populate();self.show_step(3)
                self.status.setText(f'Waybill · {len(self.waybill_fields)} field diperiksa · {len(self.diffs)} temuan individual · Stabilo dan filter memakai data temuan yang sama.')
                return
            self.reference_raw,_=read_blocks(self.ref_path,self.work);self.examined,_=read_blocks(self.exam_path,self.work)
            parsed=parse_embedded(self.reference_raw);self.reference=parsed.blocks;self.rule_groups=parsed.groups
            self.mode=self.rule_mode.currentData()
            active=resolve_scope(parsed,self.scope,self.mode,self.all_scope.isChecked())
            if not active:raise ValueError('Tidak ada parameter aktif. Pilih paragraf, tambahkan tag, atau centang seluruh dokumen.')
            self.active_scope=active
            if self.all_scope.isChecked():
                self.diffs=compare(self.reference,self.examined);self.uncertain=[]
            else:
                self.diffs,self.uncertain,_=selective_compare(self.reference,self.examined,active)
            # Separate directories avoid collisions when both inputs share a filename.
            a=self.work/'ref';b=self.work/'exam';a.mkdir(exist_ok=True);b.mkdir(exist_ok=True)
            refpdf=make_preview(self.ref_path,a);exampdf=make_preview(self.exam_path,b)
            rm,self.ref_pages,rmiss=locate(refpdf,self.diffs,'ref');em,self.exam_pages,emiss=locate(exampdf,self.diffs,'exam')
            self.ref_marks=rm;self.exam_marks=em;self.sort_differences()
            self.ref_view.load(refpdf,self.ref_marks);self.exam_view.load(exampdf,self.exam_marks);self.populate();self.show_step(3)
            self.status.setText(f'Cakupan {len(self.active_scope)}/{len(self.reference)} blok · {len(self.diffs)} perbedaan · {len(self.uncertain)} tidak terpetakan (perlu tinjauan) · Penanda {len(rm)}/{len(em)}.')
        except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def sort_differences(self):
        # Sort by physical position of the examined document, falling back to reference.
        # Keep difference indices, marker IDs and page maps consistent after sorting.
        old=list(self.diffs)
        def position(i):
            marks=[m for m in self.exam_marks if m['id']==i+1]
            if not marks:marks=[m for m in self.ref_marks if m['id']==i+1]
            if marks:
                m=marks[0];r=m['rect']
                return (m['page'],round(r.y0/12),r.x0,r.y0,i)
            return (10**7,10**7,10**7,10**7,i)
        order=sorted(range(len(old)),key=position)
        remap={old_i+1:new_i+1 for new_i,old_i in enumerate(order)}
        self.diffs=[old[i] for i in order]
        for marks in (self.ref_marks,self.exam_marks):
            for m in marks:m['id']=remap[m['id']]
        self.ref_pages={remap[k]:v for k,v in self.ref_pages.items()}
        self.exam_pages={remap[k]:v for k,v in self.exam_pages.items()}

    def populate(self,*args):
        """Group discrepancies by Waybill field; filter individual findings, not parents."""
        self.list.blockSignals(True)
        self.list.clear()
        current_filter=self.filter.currentText()
        self.visible=[]
        if self.waybill_mode:
            groups={}
            for i,d in enumerate(self.diffs):
                if current_filter == 'Perubahan' and d.kind not in ('Perubahan','Hilang','Berlebih'):continue
                groups.setdefault(d.field or 'Lainnya',[]).append((i,d))
            for field,entries in groups.items():
                kinds={k:sum(d.kind==k for _,d in entries) for k in ('Perubahan','Hilang','Berlebih')}
                summary=' · '.join(f'{count} {kind}' for kind,count in kinds.items() if count)
                parent=QTreeWidgetItem([f'{field}  ({len(entries)} temuan)  ·  {summary}'])
                parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                self.list.addTopLevelItem(parent)
                for i,d in entries:
                    snippet=(d.examined_text or d.reference_text).replace('\n',' ')[:85]
                    item=QTreeWidgetItem([f'#{i+1} · {d.kind}  —  {snippet}'])
                    item.setData(0,Qt.ItemDataRole.UserRole,i)
                    item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(0,Qt.CheckState.Checked if d.apply else Qt.CheckState.Unchecked)
                    parent.addChild(item)
                parent.setExpanded(True)
        else:
            for i,d in enumerate(self.diffs):
                if current_filter == 'Perubahan' and d.kind not in ('Perubahan','Hilang','Berlebih'):continue
                label=(d.examined_text or d.reference_text).replace('\n',' ')[:95]
                item=QTreeWidgetItem([f'#{i+1} · {d.kind}  —  {label}'])
                item.setData(0,Qt.ItemDataRole.UserRole,i)
                item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0,Qt.CheckState.Checked if d.apply else Qt.CheckState.Unchecked)
                self.list.addTopLevelItem(item)
        self.list.blockSignals(False)
        try:self.list.itemChanged.disconnect(self.changed)
        except (RuntimeError,TypeError):pass
        self.list.itemChanged.connect(self.changed)
    def changed(self,item,column):
        index=item.data(0,Qt.ItemDataRole.UserRole)
        if index is None:return
        self.diffs[index].apply=item.checkState(0)==Qt.CheckState.Checked
        if self.editor_text is not None:
            self.status.setText('Pilihan koreksi berubah. Editor sebelumnya tetap tersimpan; buka Editor untuk meninjaunya.')
    def navigate_tree(self,item,column):
        index=item.data(0,Qt.ItemDataRole.UserRole)
        if index is None:
            item.setExpanded(not item.isExpanded());return
        self.navigate(index)
    def navigate(self,i):
        if i<0 or i>=len(self.diffs):return
        d=self.diffs[i];n=i+1
        if n in self.ref_pages:self.ref_view.goto(self.ref_pages[n])
        if n in self.exam_pages:self.exam_view.goto(self.exam_pages[n])
        self.detail.setText(f'#{n} · {d.kind}' + (f' · {d.field}' if getattr(d,'field','') else '') +
            f'\n\nRujukan: {d.reference_text[:240] or "(tidak ada)"}\n\nDiperiksa: {d.examined_text[:240] or "(hilang)"}\n\nCatatan: posisi teks hasil ekstraksi PDF perlu diverifikasi manual.')
    def ensure(self):
        if self.waybill_mode and self.sender() in (self.apply_btn,self.pdf_btn):
            QMessageBox.warning(self,'Ekspor koreksi Waybill','Ekspor koreksi otomatis belum aman untuk PDF Waybill. Ekspor laporan JSON tersedia.');return False
        if not self.diffs:QMessageBox.warning(self,'Belum dibandingkan','Jalankan perbandingan terlebih dahulu.');return False
        return True
    def open_editor(self):
        if not self.exam_path or not self.reference:
            QMessageBox.warning(self,'Belum siap','Pilih dokumen dan jalankan perbandingan terlebih dahulu.');return
        if self.waybill_mode:
            QMessageBox.information(self,'Mode Waybill','Editor dan koreksi otomatis PDF tidak tersedia pada mode Waybill. Gunakan hasil audit untuk koreksi manual pada dokumen sumber.');return
        source=corrected_blocks(self.examined,self.diffs)
        if self.editor_text is None:
            self.editor_initial=list(source)
            self.editor_text='\n'.join(source)
            self.editor_source=list(self.examined)
        dialog=CorrectionEditor(self.editor_text,self.editor_initial,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.editor_text=dialog.content()
            self.status.setText('Perubahan manual tersimpan dalam sesi ini. Ekspor DOCX/PDF untuk menyimpan ke berkas.')

    def output_blocks(self):
        if self.editor_text is not None:
            return self.editor_text.split('\n')
        return corrected_blocks(self.examined,self.diffs)

    def export_docx(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan DOCX','docmatch_hasil.docx','DOCX (*.docx)')
        if name:
            try:save_annotated_docx(self.output_blocks(),Path(name),self.editor_source or self.examined);QMessageBox.information(self,'Selesai','DOCX disimpan. Paragraf yang berubah diberi stabilo. Layout asli belum dipertahankan.')
            except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def export_pdf(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan PDF','docmatch_hasil.pdf','PDF (*.pdf)')
        if name:
            try:
                src=self.work/'corrected.docx';save_annotated_docx(self.output_blocks(),src,self.editor_source or self.examined)
                pdf=libreoffice_convert(src,'pdf',self.work);shutil.copyfile(pdf,name)
                QMessageBox.information(self,'Selesai','PDF berhasil disimpan.')
            except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def export_report(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan laporan','docmatch_laporan.json','JSON (*.json)')
        if name:
            report={'reference':str(self.ref_path),'examined':str(self.exam_path),'scope':{'mode':self.mode,'waybill_fields':sorted(self.waybill_fields) if self.waybill_mode else [],'selected_reference_blocks':[i+1 for i in sorted(self.active_scope)],'unchecked_reference_blocks':[i+1 for i in range(len(self.reference)) if i not in self.active_scope],'unmapped_reference_blocks':[i+1 for i in self.uncertain],'embedded_groups':self.rule_groups},'manual_editor':{'used':self.editor_text is not None,'edited_text':self.editor_text if self.editor_text is not None else None},'limitations':'Waybill: ekstraksi berdasarkan koordinat template ANL, belum universal; koreksi PDF tidak otomatis. Mode umum: ekspor membangun ulang teks dan tidak menjaga layout asli.','differences':[
                {**asdict(d),'number':i+1,'reference_page':self.ref_pages.get(i+1, -1)+1 if i+1 in self.ref_pages else None,
                 'examined_page':self.exam_pages.get(i+1,-1)+1 if i+1 in self.exam_pages else None} for i,d in enumerate(self.diffs)]}
            Path(name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            QMessageBox.information(self,'Selesai','Laporan disimpan.')

if __name__=='__main__':
    app=QApplication(sys.argv);w=Window();w.show();sys.exit(app.exec())
