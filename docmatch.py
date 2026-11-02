"""DocMatch v0.4: local desktop visual document comparison."""
from __future__ import annotations
import sys, tempfile, shutil, json, difflib, re, io, zipfile
from pathlib import Path
from dataclasses import asdict
import pymupdf as fitz
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QFont, QTextCursor, QTextCharFormat, QBrush
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QFileDialog,QSplitter,QScrollArea,QListWidget,QListWidgetItem,QMessageBox,QComboBox,QFrame,QCheckBox,QDialog,QDialogButtonBox,QTextEdit,QPlainTextEdit,QStackedWidget,QTreeWidget,QTreeWidgetItem)
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

def full_line_correction(pdf, page_no, examined_fragment, reference_fragment, kind='Perubahan'):
    """Build a contextual note from the examined PDF's actual text line.

    Only replace an unambiguous exact token/phrase; otherwise preserve the
    reference fragment so the user can review the note manually.
    """
    fallback = reference_fragment.strip() or '[HAPUS TEKS BERLEBIH]'
    if kind != 'Perubahan' or not examined_fragment.strip():
        return fallback
    if page_no is None or not (0 <= page_no < len(pdf)):
        return fallback
    page = pdf[page_no]
    old = ' '.join(examined_fragment.split())
    new = ' '.join(reference_fragment.split())
    if not new:
        return fallback
    # Extract original visual lines, not a text dump: this keeps unrelated
    # table columns and the next lines out of the suggested correction.
    lines = []
    for block in page.get_text('dict').get('blocks', []):
        if 'lines' not in block:
            continue
        for line in block['lines']:
            spans = line.get('spans', [])
            content = ''.join(span.get('text', '') for span in spans).strip()
            if content:
                lines.append(content)
    # Match whole tokens where possible. This avoids replacing PT inside
    # another word or a similar number elsewhere in the Waybill.
    pattern = re.compile(r'(?<!\w)' + re.escape(old) + r'(?!\w)', re.IGNORECASE)
    candidates = [line for line in lines if pattern.search(line)]
    if len(candidates) == 1 and len(pattern.findall(candidates[0])) == 1:
        return pattern.sub(lambda _m: new, candidates[0], count=1)
    # PDF text sometimes splits a word across spans or OCR-like fragments.
    # Do not invent surrounding words when the source line is ambiguous.
    return fallback

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('DocMatch v1.3 — Step Wizard (Offline)');self.resize(1100,740)
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
        self.editor_text=None;self.editor_initial=None;self.editor_source=None;self.note_overrides={}
        self.apply_btn=QPushButton('Ekspor DOCX / Laporan Waybill');self.apply_btn.setObjectName('primary');self.apply_btn.clicked.connect(self.export_docx)
        self.notes_btn=QPushButton('Preview & Edit Catatan Koreksi…');self.notes_btn.clicked.connect(self.visual_correction_notes);s.addWidget(self.notes_btn)
        self.pdf_btn=QPushButton('Ekspor Hasil Pemeriksaan PDF…');self.pdf_btn.clicked.connect(self.export_pdf)
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
        self.editor_text=None;self.editor_initial=None;self.editor_source=None;self.note_overrides={}
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
        if not self.diffs:
            QMessageBox.warning(self,'Belum dibandingkan','Jalankan perbandingan terlebih dahulu.');return False
        return True
    def export_waybill_pdf(self, target, side='exam'):
        """Export a non-destructive annotated copy of either source PDF."""
        if side not in ('ref', 'exam'):
            raise ValueError('Sisi dokumen tidak dikenal.')
        viewer = self.ref_view if side == 'ref' else self.exam_view
        marks = self.ref_marks if side == 'ref' else self.exam_marks
        if not viewer.pdf:
            raise ValueError('Preview PDF belum tersedia. Jalankan perbandingan dahulu.')
        with fitz.open() as output:
            output.insert_pdf(viewer.pdf)
            for mark in marks:
                pno = mark['page']
                if pno < 0 or pno >= len(output):
                    continue
                rect = fitz.Rect(mark['rect'])
                if rect.is_empty or rect.is_infinite:
                    continue
                kind = mark.get('kind', 'Perubahan')
                rgb = {'Perubahan': (0.91, 0.29, 0.37),
                       'Hilang': (0.96, 0.73, 0.24),
                       'Berlebih': (0.22, 0.60, 0.91)}.get(kind, (0.91, 0.29, 0.37))
                page = output[pno]
                shape = page.new_shape()
                shape.draw_rect(rect)
                shape.finish(color=rgb, fill=rgb, fill_opacity=0.24,
                             stroke_opacity=0.60, width=0.4)
                shape.commit(overlay=True)
            meta = dict(output.metadata or {})
            meta['subject'] = 'DocMatch Waybill - salinan audit beranotasi, bukan koreksi otomatis'
            output.set_metadata(meta)
            output.save(str(target), garbage=3, deflate=True)

    def choose_pdf_export_documents(self):
        """Choose any combination of the four PDF output types."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Ekspor Hasil Pemeriksaan PDF — Waybill')
        dialog.resize(590, 350)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Pilih satu atau beberapa dokumen untuk diekspor:'))
        choices = [
            ('ref', 'Dokumen Rujukan — PDF beranotasi'),
            ('exam', 'Dokumen Diperiksa — PDF beranotasi'),
            ('corrected', 'Hasil Koreksi Bersih — penggantian teks yang disetujui'),
            ('notes', 'Hasil Koreksi dengan Catatan — stabilo dan catatan di margin kanan'),
        ]
        boxes = []
        for key, label in choices:
            cb = QCheckBox(label)
            cb.setChecked(key in ('ref', 'exam'))
            layout.addWidget(cb)
            boxes.append((key, cb))
        row = QHBoxLayout()
        all_btn = QPushButton('Pilih Semua')
        none_btn = QPushButton('Hapus Semua')
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for _, cb in boxes])
        none_btn.clicked.connect(lambda: [cb.setChecked(False) for _, cb in boxes])
        row.addWidget(all_btn); row.addWidget(none_btn); row.addStretch()
        layout.addLayout(row)
        note = QLabel('Koreksi Bersih hanya untuk perubahan yang disetujui dan aman.\n'
                      'Koreksi dengan Catatan mempertahankan teks asli; hanya temuan yang dicentang yang diberi catatan.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        selected = [key for key, cb in boxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, 'Belum memilih', 'Pilih minimal satu dokumen.')
            return None
        return selected

    def export_waybill_corrected_pdf(self, target):
        """Conservative replacement: only unique, one-line, explicitly approved substitutions.

        Never silently convert a missing/extra token into a destructive PDF edit.
        """
        approved = [(i + 1, d) for i, d in enumerate(self.diffs) if d.apply]
        if not approved:
            raise ValueError('Belum ada koreksi yang disetujui. Centang temuan yang akan dikoreksi.')
        planned = []
        rejected = []
        for number, diff in approved:
            old = diff.examined_text.strip()
            new = diff.reference_text.strip()
            hits = [m for m in self.exam_marks if m['id'] == number]
            if (diff.kind != 'Perubahan' or not old or not new or
                len(old.split()) != 1 or len(new.split()) != 1 or len(hits) != 1):
                rejected.append(number)
                continue
            hit = hits[0]
            page = self.exam_view.pdf[hit['page']]
            rect = fitz.Rect(hit['rect'])
            # Validate that the highlighted rectangle really contains exactly the old token.
            extracted = page.get_textbox(rect).strip()
            if extracted != old or rect.width < 8 or rect.height < 4:
                rejected.append(number)
                continue
            # Avoid overlapping replacement rectangles.
            if any(hit['page'] == pno and rect.intersects(other) for pno, other, _, _ in planned):
                rejected.append(number)
                continue
            planned.append((hit['page'], rect, old, new))
        if rejected:
            raise ValueError('Ekspor koreksi dibatalkan: temuan #' + ', #'.join(map(str,rejected)) +
                ' belum aman untuk diganti otomatis. Gunakan PDF beranotasi untuk audit. '
                'Koreksi Waybill multi-kata/angka dalam tabel memerlukan editor posisi khusus.')
        with fitz.open() as output:
            output.insert_pdf(self.exam_view.pdf)
            for pno, rect, old, new in planned:
                page = output[pno]
                # Keep image and vector graphics; remove text only within the validated region.
                page.add_redact_annot(rect, fill=False, cross_out=False)
            for page in output:
                page.apply_redactions(images=0, graphics=0, text=0)
            for pno, rect, old, new in planned:
                page = output[pno]
                # Fit replacement into the existing bounding box; abort rather than overflow.
                font_size = min(10.0, rect.height * 0.75)
                if fitz.get_text_length(new, fontname='helv', fontsize=font_size) > rect.width:
                    raise ValueError(f'Teks pengganti "{new}" tidak muat di kotak asli. Ekspor dibatalkan.')
                page.insert_text((rect.x0, rect.y1 - rect.height * 0.20), new,
                                 fontname='helv', fontsize=font_size, color=(0,0,0), overlay=True)
            meta = dict(output.metadata or {})
            meta['subject'] = 'DocMatch - koreksi PDF terbatas yang disetujui; periksa hasil secara visual'
            output.set_metadata(meta)
            output.save(str(target), garbage=3, deflate=True)

    def default_correction_note(self, number):
        diff = self.diffs[number - 1]
        if not self.waybill_mode or not self.exam_view.pdf:
            return diff.reference_text
        pages = [m['page'] for m in self.exam_marks if m['id'] == number]
        page_no = pages[0] if pages else None
        return full_line_correction(self.exam_view.pdf, page_no,
                                    diff.examined_text, diff.reference_text, diff.kind)

    def visual_correction_notes(self):
        """In-place editing of the red note boxes on a rendered annotated PDF.

        The PDF is a preview only. Changes are kept in note_overrides and the
        final export is regenerated as vector PDF using the existing writer.
        """
        if not self.ensure():
            return
        if not self.waybill_mode:
            QMessageBox.information(self, 'Mode Waybill', 'Preview catatan tersedia pada mode Waybill.')
            return
        if not self.exam_view.pdf:
            QMessageBox.warning(self, 'PDF belum tersedia', 'Jalankan pemeriksaan terlebih dahulu.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('DocMatch v1.2 — Edit Langsung di Kotak Merah')
        dialog.resize(1380, 850)
        root = QVBoxLayout(dialog)
        root.addWidget(QLabel('Klik dan ketik langsung pada kotak catatan merah. PDF asli tetap utuh.'))
        bar = QHBoxLayout()
        prev = QPushButton('‹ Halaman sebelumnya')
        next_btn = QPushButton('Halaman berikutnya ›')
        page_label = QLabel()
        bar.addWidget(prev); bar.addWidget(page_label); bar.addWidget(next_btn)
        bar.addStretch()
        root.addLayout(bar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        canvas = QLabel()
        canvas.setStyleSheet('background:white')
        scroll.setWidget(canvas)
        root.addWidget(scroll, 1)
        footer = QHBoxLayout()
        save_btn = QPushButton('Simpan Perubahan')
        export_btn = QPushButton('Ekspor PDF Catatan yang Diedit…')
        close_btn = QPushButton('Tutup')
        for btn in (save_btn, export_btn, close_btn): footer.addWidget(btn)
        root.addLayout(footer)
        working = {i + 1: self.note_overrides.get(i + 1, self.default_correction_note(i + 1))
                   for i, d in enumerate(self.diffs)}
        # Only selected findings with actual PDF positions can be drawn.
        marks_by_page = {}
        for m in self.exam_marks:
            n = m['id']
            if 1 <= n <= len(self.diffs) and self.diffs[n-1].apply:
                marks_by_page.setdefault(m['page'], {}).setdefault(n, []).append(m['rect'])
        if not marks_by_page:
            QMessageBox.warning(self, 'Tanpa catatan', 'Pilih temuan yang memiliki stabilo pada PDF terlebih dahulu.')
            return
        state = {'page': 0, 'editors': [], 'pdf': None}
        zoom = 1.35
        def commit():
            for number, editor in state['editors']:
                working[number] = editor.toPlainText()
            self.note_overrides = dict(working)
        def refresh():
            commit()
            for _, editor in state['editors']:
                editor.setParent(None)
                editor.deleteLater()
            state['editors'] = []
            if state['pdf'] is not None:
                state['pdf'].close()
                state['pdf'] = None
            # Re-render using the SAME PDF writer as the export, so positions
            # and line connectors match the actual exported document.
            self.note_overrides = dict(working)
            with tempfile.TemporaryDirectory(prefix='docmatch_visual_') as td:
                target = Path(td) / 'preview.pdf'
                self.export_waybill_notes_pdf(target)
                state['pdf'] = fitz.open(target)
            pdf = state['pdf']
            page_no = state['page']
            page = pdf[page_no]
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom * 1.5, zoom * 1.5), alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                         QImage.Format.Format_RGB888).copy()
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(1.5)
            canvas.setPixmap(pm)
            canvas.resize(pm.deviceIndependentSize().toSize())
            # Red-bordered rectangles are drawn by export_waybill_notes_pdf.
            original_width = self.exam_view.pdf[page_no].rect.width
            note_rects = []
            for drawing in page.get_drawings():
                rect = drawing.get('rect')
                if (rect is not None and rect.x0 > original_width + 7 and
                    rect.width > 90 and rect.height > 22 and
                    drawing.get('fill') is not None):
                    note_rects.append(rect)
            note_rects.sort(key=lambda r: (r.y0, r.x0))
            groups = marks_by_page.get(page_no, {})
            numbers = sorted(groups, key=lambda n: min(r.y0 for r in groups[n]))
            if len(note_rects) != len(numbers):
                # Never silently connect an editor to the wrong correction.
                raise ValueError('Tidak dapat mencocokkan kotak catatan dengan temuan. '
                                 'Gunakan editor daftar untuk dokumen ini.')
            for number, rect in zip(numbers, note_rects):
                editor = QPlainTextEdit(canvas)
                editor.setPlainText(working[number])
                editor.setToolTip(f'Catatan #{number:02d} — ketik untuk mengubah')
                editor.setStyleSheet('QPlainTextEdit { background: #FFF9F6; color: #850D1C; '
                                     'border: 1px solid #BD8A91; font: italic 12px Arial; '
                                     'padding: 3px; } QPlainTextEdit:focus { border: 2px solid #850D1C; }')
                x = round((rect.x0 + 4) * zoom)
                y = round((rect.y0 + 17) * zoom)
                w = max(85, round((rect.width - 8) * zoom))
                h = max(26, round((rect.height - 20) * zoom))
                editor.setGeometry(x, y, w, h)
                editor.show()
                state['editors'].append((number, editor))
            page_label.setText(f'Halaman {page_no+1} / {len(pdf)} · {len(numbers)} catatan dapat diedit')
            prev.setEnabled(page_no > 0)
            next_btn.setEnabled(page_no + 1 < len(pdf))
        def navigate(delta):
            commit()
            state['page'] += delta
            try:
                refresh()
            except Exception as exc:
                QMessageBox.critical(dialog, 'Preview gagal', str(exc))
        def export():
            commit()
            filename, _ = QFileDialog.getSaveFileName(dialog, 'Ekspor PDF hasil edit',
                'Waybill_Hasil_Koreksi_Catatan.pdf', 'PDF (*.pdf)')
            if not filename:
                return
            try:
                self.export_waybill_notes_pdf(Path(filename).with_suffix('.pdf'))
                QMessageBox.information(dialog, 'Berhasil', 'PDF dengan catatan terbaru berhasil diekspor.')
            except Exception as exc:
                QMessageBox.critical(dialog, 'Gagal ekspor', str(exc))
        prev.clicked.connect(lambda: navigate(-1))
        next_btn.clicked.connect(lambda: navigate(1))
        save_btn.clicked.connect(commit)
        export_btn.clicked.connect(export)
        close_btn.clicked.connect(dialog.accept)
        try:
            refresh()
        except Exception as exc:
            QMessageBox.warning(dialog, 'Preview tidak tersedia', str(exc))
            dialog.reject()
            self.edit_correction_notes()
            return
        dialog.exec()
        commit()
        if state['pdf'] is not None:
            state['pdf'].close()

    def edit_correction_notes(self):
        """Edit note values independently of the comparison/reference text.

        Changes persist for the current session and can be exported to JSON.
        The actual notes PDF is generated by the existing vector-preserving writer.
        """
        if not self.ensure():
            return
        if not self.waybill_mode:
            QMessageBox.information(self, 'Mode Waybill', 'Editor catatan tersedia pada mode Waybill.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Preview & Edit Catatan Koreksi — DocMatch v1.1')
        dialog.resize(900, 610)
        root = QVBoxLayout(dialog)
        root.addWidget(QLabel('Pilih temuan di kiri, ubah catatan di kanan. Teks asli PDF tidak diubah.'))
        split = QSplitter(Qt.Orientation.Horizontal)
        findings = QListWidget()
        pane = QWidget(); form = QVBoxLayout(pane)
        original = QLabel(''); original.setWordWrap(True)
        correction = QTextEdit(); correction.setPlaceholderText('Tulis catatan koreksi...')
        enabled = QCheckBox('Sertakan catatan ini pada PDF')
        form.addWidget(QLabel('Teks diperiksa:')); form.addWidget(original)
        form.addWidget(QLabel('Catatan koreksi (dapat diedit):')); form.addWidget(correction, 1)
        form.addWidget(enabled)
        split.addWidget(findings); split.addWidget(pane); split.setSizes([360, 540]); root.addWidget(split, 1)
        working = {i + 1: self.note_overrides.get(i + 1, self.default_correction_note(i + 1)) for i, d in enumerate(self.diffs)}
        active = [bool(d.apply) for d in self.diffs]
        for i, d in enumerate(self.diffs):
            findings.addItem(f'#{i+1:02d}  {getattr(d, "field", "")} · {d.kind} · {d.examined_text[:65]}')
        state = {'index': -1}
        def persist():
            i = state['index']
            if i >= 0:
                working[i + 1] = correction.toPlainText()
                active[i] = enabled.isChecked()
        def change(index):
            persist()
            state['index'] = index
            if index < 0: return
            d = self.diffs[index]
            original.setText(d.examined_text or '[Teks tidak ditemukan / hilang]')
            correction.setPlainText(working[index + 1])
            enabled.setChecked(active[index])
        findings.currentRowChanged.connect(change)
        buttons = QHBoxLayout()
        load_btn = QPushButton('Impor Catatan JSON…')
        save_btn = QPushButton('Simpan Catatan JSON…')
        export_btn = QPushButton('Simpan & Ekspor PDF Catatan…')
        done_btn = QPushButton('Simpan Perubahan')
        cancel_btn = QPushButton('Batal')
        def import_notes():
            filename, _ = QFileDialog.getOpenFileName(dialog, 'Impor laporan / catatan', '', 'JSON (*.json)')
            if not filename: return
            try:
                payload = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
                entries = payload.get('differences', [])
                if not isinstance(entries, list): raise ValueError('Format differences bukan daftar.')
                persist()
                loaded = 0
                for item in entries:
                    n = item.get('number')
                    if not isinstance(n, int) or not 1 <= n <= len(self.diffs): continue
                    d = self.diffs[n - 1]
                    if (item.get('examined_text') != d.examined_text or
                        item.get('field') != getattr(d, 'field', None)):
                        continue  # Never silently apply edits to a different finding.
                    working[n] = str(item.get('correction_note', item.get('reference_text', '')))
                    active[n - 1] = bool(item.get('apply', False))
                    loaded += 1
                state['index'] = -1
                change(findings.currentRow())
                QMessageBox.information(dialog, 'Impor selesai', f'{loaded} catatan cocok dengan hasil pemeriksaan aktif.')
            except Exception as exc:
                QMessageBox.critical(dialog, 'Gagal impor', str(exc))
        def write_json():
            persist()
            filename, _ = QFileDialog.getSaveFileName(dialog, 'Simpan catatan koreksi', 'DocMatch_Catatan_Koreksi.json', 'JSON (*.json)')
            if not filename: return
            data = {'format': 'DocMatch correction notes v1.1', 'differences': [
                {'number': i+1, 'field': getattr(d, 'field', ''), 'kind': d.kind,
                 'examined_text': d.examined_text, 'reference_text': d.reference_text,
                 'correction_note': working[i+1], 'apply': active[i]}
                for i, d in enumerate(self.diffs)]}
            Path(filename).with_suffix('.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            QMessageBox.information(dialog, 'Tersimpan', 'Catatan koreksi berhasil disimpan ke JSON.')
        def commit():
            persist()
            self.note_overrides = dict(working)
            for i, checked in enumerate(active): self.diffs[i].apply = checked
            self.populate()
        def export_notes():
            commit()
            filename, _ = QFileDialog.getSaveFileName(dialog, 'Ekspor PDF catatan yang diedit', 'Waybill_Hasil_Koreksi_Catatan.pdf', 'PDF (*.pdf)')
            if not filename: return
            try:
                target = Path(filename).with_suffix('.pdf')
                self.export_waybill_notes_pdf(target)
                QMessageBox.information(dialog, 'Ekspor berhasil', f'PDF catatan tersimpan:\n{target}')
            except Exception as exc:
                QMessageBox.critical(dialog, 'Gagal ekspor', str(exc))
        load_btn.clicked.connect(import_notes); save_btn.clicked.connect(write_json)
        export_btn.clicked.connect(export_notes)
        done_btn.clicked.connect(lambda: (commit(), dialog.accept()))
        cancel_btn.clicked.connect(dialog.reject)
        for btn in (load_btn, save_btn, export_btn, done_btn, cancel_btn): buttons.addWidget(btn)
        root.addLayout(buttons)
        if self.diffs: findings.setCurrentRow(0)
        dialog.exec()

    def export_waybill_notes_pdf(self, target):
        """Non-destructive, vector-preserving PDF with right-margin correction notes.

        Only explicitly checked findings are annotated. The source PDF is never modified.
        Each note is linked to its original highlighted rectangle. A note that cannot
        be placed safely fails the export rather than obscuring document content.
        """
        if not self.exam_view.pdf:
            raise ValueError('PDF dokumen diperiksa belum tersedia.')
        approved = {i + 1: d for i, d in enumerate(self.diffs) if d.apply}
        if not approved:
            raise ValueError('Belum ada temuan yang dipilih. Centang temuan untuk diberi catatan koreksi.')
        marks_by_page = {}
        for mark in self.exam_marks:
            number = mark.get('id')
            if number in approved:
                marks_by_page.setdefault(mark['page'], []).append(mark)
        if not marks_by_page:
            raise ValueError('Temuan terpilih tidak memiliki posisi stabilo pada PDF diperiksa.')
        source = self.exam_view.pdf
        margin = 245
        with fitz.open() as output:
            for pno, original in enumerate(source):
                bounds = original.rect
                page = output.new_page(width=bounds.width + margin, height=bounds.height)
                page.show_pdf_page(fitz.Rect(0, 0, bounds.width, bounds.height), source, pno)
                marks = marks_by_page.get(pno, [])
                # Draw existing comparison highlights, including findings not selected
                # for correction, to retain the same visual audit as 'Dokumen Diperiksa'.
                for mark in (m for m in self.exam_marks if m['page'] == pno):
                    rect = fitz.Rect(mark['rect'])
                    if rect.is_empty or rect.is_infinite:
                        continue
                    rgb = {'Perubahan': (0.91, 0.29, 0.37),
                           'Hilang': (0.96, 0.73, 0.24),
                           'Berlebih': (0.22, 0.60, 0.91)}.get(mark.get('kind'), (0.91, 0.29, 0.37))
                    shape = page.new_shape()
                    shape.draw_rect(rect)
                    shape.finish(color=rgb, fill=rgb, fill_opacity=0.24,
                                 stroke_opacity=0.60, width=0.4)
                    shape.commit(overlay=True)
                if not marks:
                    continue
                page.draw_line(fitz.Point(bounds.width + 6, 15),
                               fitz.Point(bounds.width + 6, bounds.height - 15),
                               color=(0.70, 0.70, 0.70), width=0.6)
                page.insert_text((bounds.width + 17, 26), 'CATATAN KOREKSI',
                                 fontname='hebo', fontsize=10, color=(0.50, 0.05, 0.12))
                # One note per finding, even if a finding has multiple word highlights.
                groups = {}
                for mark in marks:
                    groups.setdefault(mark['id'], []).append(fitz.Rect(mark['rect']))
                sorted_groups = sorted(groups.items(), key=lambda kv: min(r.y0 for r in kv[1]))
                next_y = 43.0
                for number, rectangles in sorted_groups:
                    diff = approved[number]
                    desired = (self.note_overrides.get(number, self.default_correction_note(number)) or '').strip()
                    if not desired:
                        desired = '[HAPUS TEKS BERLEBIH]'
                    desired = ' '.join(desired.split())
                    anchor = min(rectangles, key=lambda r: (r.y0, r.x0))
                    # Estimate note height and adapt to long correction values.
                    note_width = margin - 30
                    font_size = 9.5
                    chars_per_line = max(18, int(note_width / (font_size * 0.52)))
                    import textwrap
                    lines = textwrap.wrap(desired, width=chars_per_line,
                                          break_long_words=True, break_on_hyphens=False)
                    lines = lines or ['[KOREKSI KOSONG]']
                    height = 18 + 12 * len(lines) + 9
                    top = max(next_y, min(anchor.y0, bounds.height - height - 13))
                    if top + height > bounds.height - 8:
                        raise ValueError(f'Halaman {pno+1}: catatan koreksi tidak muat di margin. '
                                         'Kurangi temuan yang dipilih atau ekspor secara terpisah.')
                    x0 = bounds.width + 14
                    rect = fitz.Rect(x0, top, bounds.width + margin - 9, top + height)
                    page.draw_rect(rect, color=(0.72, 0.52, 0.54), fill=(1, 0.98, 0.96), width=0.6)
                    page.insert_text((x0 + 6, top + 12), f'#{number:02d}  {diff.kind}',
                                     fontname='hebo', fontsize=8, color=(0.48, 0.05, 0.11))
                    text_rect = fitz.Rect(x0 + 6, top + 17, rect.x1 - 5, rect.y1 - 4)
                    result = page.insert_textbox(text_rect, desired, fontname='heit',
                                                 fontsize=font_size, lineheight=1.18,
                                                 color=(0.35, 0.06, 0.13))
                    if result < 0:
                        raise ValueError(f'Catatan #{number} tidak muat. Ekspor dibatalkan.')
                    # Leader line points to the first highlighted word of the finding.
                    page.draw_line(fitz.Point(anchor.x1, (anchor.y0 + anchor.y1)/2),
                                   fitz.Point(x0, top + 9), color=(0.55, 0.15, 0.20), width=0.65)
                    next_y = top + height + 6
            meta = dict(output.metadata or {})
            meta['subject'] = ('DocMatch - PDF diperiksa dengan stabilo dan catatan koreksi; '
                               'teks asli tidak diubah; catatan bukan penggantian PDF')
            output.set_metadata(meta)
            output.save(str(target), garbage=3, deflate=True)

    def export_waybill_docx(self,target):
        # Editable findings with a faithful image of each original page. PDF text is NOT rebuilt as editable layout.
        from docx import Document
        from docx.shared import Inches,Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        doc=Document();section=doc.sections[0]
        section.top_margin=Inches(.55);section.bottom_margin=Inches(.55)
        section.left_margin=Inches(.65);section.right_margin=Inches(.65)
        doc.add_heading('DocMatch — Laporan Pemeriksaan Waybill',0)
        doc.add_paragraph('Dokumen diperiksa: '+str(self.exam_path.name))
        doc.add_paragraph('Dokumen rujukan: '+str(self.ref_path.name))
        doc.add_paragraph('Status: laporan audit, BUKAN dokumen Waybill yang sudah dikoreksi otomatis. Teks temuan dapat diedit pada tabel di bawah.')
        doc.add_heading('Daftar temuan (dapat diedit)',level=1)
        table=doc.add_table(rows=1,cols=5);table.style='Table Grid';table.alignment=WD_TABLE_ALIGNMENT.CENTER
        for cell,text in zip(table.rows[0].cells,['No.','Field','Kategori','Rujukan','Diperiksa']):cell.text=text
        for i,d in enumerate(self.diffs,1):
            row=table.add_row()
            for cell,text in zip(row.cells,[str(i),str(getattr(d,'field','')),str(d.kind),str(d.reference_text),str(d.examined_text)]):cell.text=text
        doc.add_page_break();doc.add_heading('Lampiran — Halaman Waybill yang ditandai',level=1)
        if not self.exam_view.pdf:raise ValueError('Preview PDF belum tersedia')
        pdf=self.exam_view.pdf
        for pno,page in enumerate(pdf):
            doc.add_heading(f'Halaman {pno+1}',level=2)
            # Rasterize a marked copy for the visual appendix; source PDF remains unchanged.
            with fitz.open() as one:
                one.insert_pdf(pdf,from_page=pno,to_page=pno)
                for mark in self.exam_marks:
                    if mark['page']!=pno:continue
                    rect=fitz.Rect(mark['rect']);kind=mark.get('kind','Perubahan')
                    rgb={'Perubahan':(0.91,0.29,0.37),'Hilang':(0.96,0.73,0.24),'Berlebih':(0.22,0.60,0.91)}.get(kind,(0.91,0.29,0.37))
                    sh=one[0].new_shape();sh.draw_rect(rect);sh.finish(color=rgb,fill=rgb,fill_opacity=.24,width=.4);sh.commit()
                pix=one[0].get_pixmap(matrix=fitz.Matrix(1.8,1.8),alpha=False)
                stream=io.BytesIO(pix.tobytes('png'))
                usable=section.page_width-section.left_margin-section.right_margin
                doc.add_picture(stream,width=usable)
            if pno<len(pdf)-1:doc.add_page_break()
        doc.save(str(target))
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
            try:
                if self.waybill_mode:
                    self.export_waybill_docx(name)
                    QMessageBox.information(self,'Selesai','Laporan DOCX Waybill disimpan: tabel temuan dapat diedit, halaman Waybill adalah gambar beranotasi. Ini bukan koreksi otomatis pada dokumen asli.')
                else:
                    save_annotated_docx(self.output_blocks(),Path(name),self.editor_source or self.examined)
                    QMessageBox.information(self,'Selesai','DOCX disimpan. Paragraf yang berubah diberi stabilo. Layout asli belum dipertahankan.')
            except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def export_pdf(self):
        if not self.ensure():
            return
        if self.waybill_mode:
            selected = self.choose_pdf_export_documents()
            if selected is None:
                return
            outputs = {
                'ref': ('Waybill_Rujukan_Beranotasi.pdf', lambda path: self.export_waybill_pdf(path, 'ref')),
                'exam': ('Waybill_Diperiksa_Beranotasi.pdf', lambda path: self.export_waybill_pdf(path, 'exam')),
                'corrected': ('Waybill_Hasil_Koreksi_Bersih.pdf', self.export_waybill_corrected_pdf),
                'notes': ('Waybill_Hasil_Koreksi_Catatan.pdf', self.export_waybill_notes_pdf),
            }
            is_zip = len(selected) > 1
            default = 'DocMatch_Hasil_PDF.zip' if is_zip else outputs[selected[0]][0]
            file_filter = 'ZIP (*.zip)' if is_zip else 'PDF (*.pdf)'
            name, _ = QFileDialog.getSaveFileName(self, 'Simpan hasil pemeriksaan', default, file_filter)
            if not name:
                return
            target = Path(name)
            target = target.with_suffix('.zip' if is_zip else '.pdf')
            try:
                with tempfile.TemporaryDirectory(prefix='docmatch_export_') as td:
                    produced = []
                    for key in selected:
                        filename, writer = outputs[key]
                        output_path = Path(td) / filename
                        writer(output_path)
                        produced.append(output_path)
                    if is_zip:
                        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for path in produced:
                                zf.write(path, path.name)
                    else:
                        shutil.copyfile(produced[0], target)
                QMessageBox.information(self, 'Selesai', f'{len(selected)} dokumen berhasil diekspor ke:\n{target}')
            except Exception as e:
                QMessageBox.critical(self, 'Ekspor dibatalkan', str(e))
            return
        name, _ = QFileDialog.getSaveFileName(self, 'Simpan PDF',
                                               'docmatch_hasil.pdf', 'PDF (*.pdf)')
        if name:
            try:
                src = self.work / 'corrected.docx'
                save_annotated_docx(self.output_blocks(), src,
                                    self.editor_source or self.examined)
                pdf = libreoffice_convert(src, 'pdf', self.work)
                shutil.copyfile(pdf, name)
                QMessageBox.information(self, 'Selesai', 'PDF berhasil disimpan.')
            except Exception as e:
                QMessageBox.critical(self, 'Gagal', str(e))
    def export_report(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan laporan','docmatch_laporan.json','JSON (*.json)')
        if name:
            report={'reference':str(self.ref_path),'examined':str(self.exam_path),'scope':{'mode':self.mode,'waybill_fields':sorted(self.waybill_fields) if self.waybill_mode else [],'selected_reference_blocks':[i+1 for i in sorted(self.active_scope)],'unchecked_reference_blocks':[i+1 for i in range(len(self.reference)) if i not in self.active_scope],'unmapped_reference_blocks':[i+1 for i in self.uncertain],'embedded_groups':self.rule_groups},'manual_editor':{'used':self.editor_text is not None,'edited_text':self.editor_text if self.editor_text is not None else None},'limitations':'Waybill: ekspor PDF merupakan salinan audit beranotasi, bukan koreksi otomatis; DOCX berisi tabel temuan editable dan gambar halaman. Ekstraksi berbasis template ANL belum universal. Mode umum membangun ulang teks.','differences':[
                {**asdict(d),'number':i+1,'reference_page':self.ref_pages.get(i+1, -1)+1 if i+1 in self.ref_pages else None,
                 'examined_page':self.exam_pages.get(i+1,-1)+1 if i+1 in self.exam_pages else None} for i,d in enumerate(self.diffs)]}
            Path(name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            QMessageBox.information(self,'Selesai','Laporan disimpan.')

if __name__=='__main__':
    app=QApplication(sys.argv);w=Window();w.show();sys.exit(app.exec())
