"""DocMatch v0.4: local desktop visual document comparison."""
from __future__ import annotations
import sys, tempfile, shutil, json, difflib, re, io, zipfile, copy, logging, traceback
from datetime import datetime, timezone
from collections import OrderedDict
from pathlib import Path
from dataclasses import asdict
import pymupdf as fitz
from PySide6.QtCore import Qt, QSize, QRectF, QTimer, QStandardPaths, QEvent
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QFont, QTextCursor, QTextCharFormat, QBrush, QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QFileDialog,QSplitter,QScrollArea,QListWidget,QListWidgetItem,QMessageBox,QComboBox,QFrame,QCheckBox,QDialog,QDialogButtonBox,QTextEdit,QPlainTextEdit,QStackedWidget,QTreeWidget,QTreeWidgetItem,QSplashScreen,QLineEdit,QTabWidget,QInputDialog)
from legacy_v01 import read_blocks, compare, corrected_blocks, save_docx, libreoffice_convert, Difference
from rules import parse_embedded, resolve_scope, selective_compare
from editor import CorrectionEditor, save_annotated_docx
from waybill_rules import FIELDS, compare_waybills, profile_field_names, WaybillDifference
from cross_carrier import PROFILES, PROFILE_LABELS
from hybrid_validation import HybridValidationDialog
import waybill_rules as swb_rules
from session_store import save_session, load_session, fingerprint
from template_manager import read_templates, write_templates, validate_templates
from ui_layout_state import group_check_state, responsive_split_widths
from correction_note_layout import NOTE_MARGIN, note_box_layout
from correction_markers import draw_number_marker, scan_ink_guard
from correction_preview import CorrectionPreview
from export_naming import correction_pdf_filename
from reference_note_format import (address_reference_values, is_address_field,
                                   structured_reference_values, is_structured_field)

def pdf_json_default(value):
    """Convert PyMuPDF geometry to JSON primitives without losing coordinates."""
    if isinstance(value, fitz.Rect) or isinstance(value, fitz.IRect):
        return [value.x0, value.y0, value.x1, value.y1]
    if isinstance(value, fitz.Point):
        return [value.x, value.y]
    if isinstance(value, fitz.Quad):
        return [list(point) for point in (value.ul, value.ur, value.ll, value.lr)]
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def set_windows_app_id() -> None:
    """Keep the DocMatch icon on the Windows taskbar instead of a Python icon."""
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('DocMatch.Desktop.Portable.1')
        except (AttributeError, OSError):
            pass


def app_icon() -> QIcon:
    """Load the bundled ICO, falling back to PNG for non-Windows platforms."""
    for name in ('docmatch.ico', 'docmatch_128.png', 'docmatch_logo.png'):
        candidate = asset_path(name)
        if candidate.is_file():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def asset_path(name: str) -> Path:
    """Resolve branding assets in source and PyInstaller builds."""
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return root / 'assets' / name

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
        super().__init__(); self.pdf=None; self.page=0; self.zoom=1.15; self.marks=[]; self.stage2_marks=[]; self.hidden_stage2_fields=set(); self.mark_field_map={}; self.title=title; self.highlights=True; self._page_cache=OrderedDict(); self._page_cache_limit=3; self.fit_mode=True
        self.setObjectName('paperPanel')
        lay=QVBoxLayout(self); lay.setContentsMargins(10,10,10,10); lay.setSpacing(8)
        bar=QHBoxLayout(); self.heading=QLabel(title); self.heading.setStyleSheet('font-weight:700')
        bar.addWidget(self.heading); bar.addStretch()
        self.prev=QPushButton('‹');self.next=QPushButton('›');self.counter=QLabel('0 / 0')
        self.minus=QPushButton('−');self.plus=QPushButton('+');self.fit_btn=QPushButton('Lebar');self.fit_btn.setToolTip('Sesuaikan halaman PDF dengan lebar panel');self.toggle=QCheckBox('Stabilo');self.toggle.setChecked(True)
        for w in (self.prev,self.counter,self.next,self.minus,self.plus,self.fit_btn,self.toggle):bar.addWidget(w)
        lay.addLayout(bar)
        self.scroll=QScrollArea();self.scroll.setObjectName('paperScroll');self.scroll.setWidgetResizable(False);self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop);self.scroll.viewport().installEventFilter(self)
        self.canvas=QLabel('Pilih dokumen lalu klik Bandingkan');self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setObjectName('paperPage');self.canvas.setStyleSheet('background:white; color:#6B7280;border:1px solid #D4D9E0;');self.canvas.setMinimumSize(240,320)
        self.scroll.setWidget(self.canvas);lay.addWidget(self.scroll,1)
        self.prev.clicked.connect(lambda:self.goto(self.page-1));self.next.clicked.connect(lambda:self.goto(self.page+1))
        self.plus.clicked.connect(lambda:self.set_zoom(self.zoom+.15));self.minus.clicked.connect(lambda:self.set_zoom(self.zoom-.15));self.fit_btn.clicked.connect(self.fit_width)
        self.toggle.toggled.connect(self.set_highlights)
    def set_highlights(self,enabled):self.highlights=enabled;self.render()
    def eventFilter(self, obj, event):
        if obj is self.scroll.viewport() and event.type() == QEvent.Type.Resize and self.fit_mode:
            QTimer.singleShot(0, self.fit_width)
        return super().eventFilter(obj, event)
    def set_zoom(self,z):
        self.fit_mode=False
        self.zoom=max(.35,min(2.3,z));self.render()
    def fit_width(self):
        self.fit_mode=True
        if not self.pdf: return
        page_width=max(1.0,float(self.pdf[self.page].rect.width))
        available=max(100,self.scroll.viewport().width()-24)
        target=max(.35,min(2.3,available/page_width))
        if abs(target-self.zoom) > .008:
            self.zoom=target
            self.render()

    def load(self,path,marks):
        if self.pdf:self.pdf.close()
        self._page_cache.clear()
        self.pdf=fitz.open(path);self.marks=marks;self.stage2_marks=[];self.page=0;self.render();QTimer.singleShot(0,self.fit_width)
    def clear(self, message='Pilih dokumen lalu klik Bandingkan'):
        if self.pdf:
            self.pdf.close()
        self.pdf=None;self.page=0;self.marks=[];self.stage2_marks=[];self._page_cache.clear()
        self.counter.setText('0 / 0')
        self.canvas.setPixmap(QPixmap())
        self.canvas.setText(message)
        self.canvas.resize(240,320)

    def goto(self,page):
        if self.pdf and 0<=page<len(self.pdf):
            self.page=page
            self.render()
            if self.fit_mode:
                QTimer.singleShot(0,self.fit_width)
    def render(self):
        if not self.pdf:return
        p=self.pdf[self.page]
        # Render at 2x the visible resolution, then let Qt downsample smoothly.
        scale=self.zoom*RENDER_QUALITY
        key=(self.page, round(scale,3))
        img=self._page_cache.get(key)
        if img is None:
            pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
            img=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
            self._page_cache[key]=img
            while len(self._page_cache)>self._page_cache_limit:
                self._page_cache.popitem(last=False)
        else:
            self._page_cache.move_to_end(key)
        # Draw annotations on a fresh copy, never on the cached clean page.
        img=img.copy()
        if self.highlights:
            painter=QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
            seen_markers=set()
            for m in self.marks:
                if self.mark_field_map.get(m.get('id')) in self.hidden_stage2_fields:continue
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
            # Stage 2 overlays are independent of discrepancy type and can be
            # toggled in the Export checklist without touching the source PDF.
            for mark in self.stage2_marks:
                if mark['page'] != self.page: continue
                rect = fitz.Rect(mark['rect']) * fitz.Matrix(scale, scale)
                painter.setBrush(QBrush(QColor(30, 120, 175, 30)))
                painter.setPen(QPen(QColor('#176AA0'), max(1.0, .85 * scale)))
                painter.drawRect(QRectF(rect.x0, rect.y0, rect.width, rect.height))
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

def full_line_correction(pdf, page_no, examined_fragment, reference_fragment, kind='Perubahan', field=''):
    """Build a contextual note from the examined PDF's actual text line.

    Only replace an unambiguous exact token/phrase; otherwise preserve the
    reference fragment so the user can review the note manually.
    """
    fallback = reference_fragment.strip() or '[HAPUS TEKS BERLEBIH]'
    # The note is a field-level suggestion, not a bare diff fragment.
    # Labels are intentionally presentation labels, not extracted PDF text.
    labels = {
        'Voyage Number': 'VOYAGE',
        'Waybill Number': 'WAYBILL',
        'Vessel': 'VESSEL',
        'Port of Loading': 'PORT OF LOADING',
        'Port of Discharge': 'PORT OF DISCHARGE',
        'Consignee': 'CONSIGNEE',
        'Notify Party': 'NOTIFY PARTY',
        'Container & Seal': 'CONTAINER & SEAL',
        'Cargo Description': 'CARGO DESCRIPTION',
        'Weight & Measurement': 'WEIGHT & MEASUREMENT',
        'Place & Date of Issue': 'PLACE & DATE OF ISSUE',
        'Additional Clauses': 'ADDITIONAL CLAUSES',
    }
    label = labels.get(field, '')
    def labeled(value):
        value = ' '.join(value.split())
        return f'{label}: {value}' if label and value else value
    if kind != 'Perubahan' or not examined_fragment.strip():
        return labeled(fallback)
    if page_no is None or not (0 <= page_no < len(pdf)):
        return labeled(fallback)
    page = pdf[page_no]
    old = ' '.join(examined_fragment.split())
    new = ' '.join(reference_fragment.split())
    if not new:
        return labeled(fallback)
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
        reconstructed = pattern.sub(lambda _m: new, candidates[0], count=1)
        # For Waybill's single-value fields, the PDF often places the field
        # heading in a different table cell/line. Always show a clear label.
        if field in {'Voyage Number', 'Waybill Number', 'Vessel', 'Port of Loading', 'Port of Discharge'}:
            return labeled(reconstructed)
        return reconstructed
    # PDF text sometimes splits a word across spans or OCR-like fragments.
    # Do not invent surrounding words when the source line is ambiguous.
    return labeled(fallback)

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('DocMatch v1.8.35.7 — Auto Portable Packaging (Offline)');self.resize(1100,740)
        self.setWindowIcon(app_icon())
        self.tmp=tempfile.TemporaryDirectory(prefix='docmatch_v03_');self.work=Path(self.tmp.name)
        self.ref_path=None;self.exam_path=None;self.reference=[];self.examined=[];self.diffs=[];self.ref_pages={};self.exam_pages={};self.checks=[];self.scope=set();self.uncertain=[];self.mode="hybrid";self.rule_groups={};self.reference_raw=[];self.waybill_fields={name for name,_ in FIELDS};self.waybill_mode=False;self.hybrid_stage2_records={};self.stage2_annotations={};self.stage2_visibility={};self._stage1_baseline=None;self.audit_events=[];self._session_file=None;self._restoring_session=False;self.has_compared=False
        root=QWidget();self.setCentralWidget(root);main=QVBoxLayout(root);main.setContentsMargins(8,5,8,6);main.setSpacing(3)
        header=QHBoxLayout()
        header.setContentsMargins(0,0,0,0)
        header.setSpacing(8)
        brand=QLabel('DocMatch');brand.setStyleSheet(f'font-size:18px;font-weight:800;color:{RED}')
        subtitle=QLabel('Pembanding & Koreksi Dokumen  •  100% Offline')
        subtitle.setStyleSheet('color:#4B5563;font-size:11px')
        header.addWidget(brand)
        header.addWidget(subtitle)
        header.addStretch()
        main.addLayout(header)
        # Step Wizard ribbon: only this top area changes; viewers and comparison engine remain intact.
        self.wizard_steps=[]
        stepbar=QHBoxLayout();stepbar.setContentsMargins(0,0,0,0);stepbar.setSpacing(6)
        for index,label in enumerate(('1  Pilih Dokumen','2  Parameter & Bandingkan','3  Hasil & Ekspor')):
            btn=QPushButton(label);btn.setObjectName('wizardStep')
            btn.clicked.connect(lambda checked=False, i=index:self.show_step(i))
            stepbar.addWidget(btn,1);self.wizard_steps.append(btn)
        main.addLayout(stepbar)
        # Session/template tools remain available in code, but are intentionally
        # hidden from the main UI to keep the workspace clean and focused.
        self.save_session_btn=QPushButton('Simpan Sesi')
        self.open_session_btn=QPushButton('Buka Sesi')
        self.template_btn=QPushButton('Template / Alias')
        self.save_session_btn.clicked.connect(self.save_session_dialog)
        self.open_session_btn.clicked.connect(self.open_session_dialog)
        self.template_btn.clicked.connect(self.open_template_manager)
        for hidden_button in (self.save_session_btn, self.open_session_btn, self.template_btn):
            hidden_button.hide()
        self.autosave_timer=QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(1200)
        self.autosave_timer.timeout.connect(self._autosave)
        self.wizard_stack=QStackedWidget()
        # The wizard is a compact contextual toolbar, never an expanding panel.
        # In Hasil & Ekspor it is hidden entirely (the ribbon owns the actions).
        self.wizard_stack.setMaximumHeight(58)
        self.wizard_stack.setMinimumHeight(0)
        main.addWidget(self.wizard_stack, 0)
        # Word-inspired contextual ribbon: visible only in Hasil & Ekspor.
        self.result_ribbon=QFrame();self.result_ribbon.setObjectName('resultRibbon')
        self.result_ribbon_layout=QHBoxLayout(self.result_ribbon)
        self.result_ribbon_layout.setContentsMargins(6,2,6,2)
        self.result_ribbon_layout.setSpacing(4)
        self.result_ribbon.hide()
        main.addWidget(self.result_ribbon)
        # Step 1: document sources
        step1=QWidget();step1_layout=QHBoxLayout(step1);step1_layout.setContentsMargins(2,7,2,7)
        self.ref_btn=QPushButton('Pilih Dokumen Rujukan');self.exam_btn=QPushButton('Pilih Dokumen Diperiksa')
        self.ref_btn.clicked.connect(lambda:self.pick('ref'));self.exam_btn.clicked.connect(lambda:self.pick('exam'))
        step1_layout.addWidget(self.ref_btn,1);step1_layout.addWidget(self.exam_btn,1)
        next1=QPushButton('Atur Parameter  →');next1.clicked.connect(lambda:self.show_step(1));step1_layout.addWidget(next1)
        self.wizard_stack.addWidget(step1)
        # Step 2: parameter selection and comparison in a single workspace.
        step2=QWidget()
        step2_layout=QVBoxLayout(step2)
        step2_layout.setContentsMargins(2,6,2,6)
        step2_layout.setSpacing(6)
        rules_bar=QHBoxLayout()
        rules_bar.setSpacing(6)
        mode_label=QLabel('Mode parameter:')
        mode_label.setStyleSheet('font-weight:600;color:#4B5563')
        rules_bar.addWidget(mode_label)
        self.rule_mode=QComboBox()
        self.rule_mode.addItem('Gabungkan tag + pilihan aplikasi','hybrid')
        self.rule_mode.addItem('Tag dokumen saja','embedded')
        self.rule_mode.addItem('Pilihan aplikasi saja','visual')
        self.rule_mode.addItem('SWB - ANL/CNC/CMA CGM','waybill_anl')
        self.rule_mode.addItem('SWB - EVERGREEN','waybill_evergreen')
        self.rule_mode.addItem('SWB - Golden Star Line','waybill_gsl')
        self.rule_mode.addItem('SWB - ONE (Ocean Network Express)','waybill_one')
        self.rule_mode.addItem('SWB - MAERSK','waybill_maersk')
        self.rule_mode.addItem('SWB - MERATUS','waybill_meratus')
        self.rule_mode.addItem('SWB - MSC (Mediterranean Shipping Company)','waybill_msc')
        self.rule_mode.setMinimumWidth(220)
        rules_bar.addWidget(self.rule_mode,1)
        self.scope_btn=QPushButton('Paragraf Rujukan')
        self.scope_btn.setToolTip('Pilih Paragraf Rujukan')
        self.scope_btn.clicked.connect(self.choose_scope)
        rules_bar.addWidget(self.scope_btn)
        self.waybill_btn=QPushButton('Field Waybill')
        self.waybill_btn.setToolTip('Atur Field Waybill')
        self.waybill_btn.clicked.connect(self.choose_waybill)
        rules_bar.addWidget(self.waybill_btn)
        self.all_scope=QCheckBox('Seluruh Dokumen')
        self.all_scope.setToolTip('Periksa seluruh dokumen')
        rules_bar.addWidget(self.all_scope)
        rules_bar.addSpacing(4)
        self.run_btn=QPushButton('⌕  Bandingkan')
        self.run_btn.setObjectName('primary')
        self.run_btn.setMinimumWidth(150)
        self.run_btn.clicked.connect(self.run)
        rules_bar.addWidget(self.run_btn)
        step2_layout.addLayout(rules_bar)
        # PDF A may be an independent shipping line. The PDF B preset above
        # always controls the examined-side fields and marker coordinates.
        self.reference_profile_bar = QWidget()
        ref_controls = QHBoxLayout(self.reference_profile_bar)
        ref_controls.setContentsMargins(1, 1, 1, 1)
        ref_controls.setSpacing(8)
        reference_label = QLabel('Profil Dokumen A (rujukan):')
        reference_label.setToolTip('Deteksi mandiri untuk PDF A; jika logo atau teks tidak dapat dibaca, pilih profil manual.')
        ref_controls.addWidget(reference_label)
        self.reference_profile_combo = QComboBox()
        self.reference_profile_combo.addItem('Deteksi Otomatis (disarankan)', 'auto')
        for profile_id, profile_label in PROFILES:
            self.reference_profile_combo.addItem('SWB - ' + profile_label, profile_id)
        self.reference_profile_combo.setToolTip('Tidak mengubah profil Dokumen B. Pilih manual jika PDF A tidak teridentifikasi.')
        self.reference_profile_combo.setMinimumWidth(220)
        ref_controls.addWidget(self.reference_profile_combo, 1)
        self.reference_profile_combo.currentIndexChanged.connect(self.mode_changed)
        step2_layout.addWidget(self.reference_profile_bar)
        self.wizard_stack.addWidget(step2)
        # Step 3: the original result page, including Word-style ribbon.
        step3=QWidget()
        step3_layout=QVBoxLayout(step3)
        step3_layout.setContentsMargins(0,0,0,0)
        step3_layout.setSpacing(0)
        self.wizard_stack.addWidget(step3)
        self.rule_mode.currentIndexChanged.connect(self.mode_changed)
        self.mode_changed()
        self.show_step(0)
        split=QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter=split
        self._preferred_inspector_width=360
        self._split_resize_queued=False
        split.setObjectName('workspaceSplitter')
        self.document_split=QSplitter(Qt.Orientation.Horizontal)
        self.document_split.setObjectName('documentSplitter')
        self.ref_view=Paper('DOKUMEN RUJUKAN');self.exam_view=Paper('DOKUMEN DIPERIKSA')
        self.document_split.addWidget(self.ref_view);self.document_split.addWidget(self.exam_view)
        self.document_split.setChildrenCollapsible(False)
        self.document_split.setStretchFactor(0,1);self.document_split.setStretchFactor(1,1)
        split.addWidget(self.document_split)

        side=QFrame();side.setObjectName('inspectorPane');side.setMinimumWidth(280)
        side.setSizePolicy(side.sizePolicy().horizontalPolicy(), side.sizePolicy().verticalPolicy())
        s=QVBoxLayout(side);s.setContentsMargins(10,10,10,10);s.setSpacing(8)
        panel_title=QLabel('PANEL PEMERIKSAAN');panel_title.setObjectName('sectionTitle');s.addWidget(panel_title)
        self.results_tabs=QTabWidget()
        self.results_tabs.setDocumentMode(True)
        # Share the limited inspector width equally between the two tabs.
        self.results_tabs.tabBar().setExpanding(True)
        self.results_tabs.tabBar().setUsesScrollButtons(False)
        self.results_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.results_tabs.setStyleSheet("""QTabBar::tab{padding:5px 4px;min-width:0px;font-weight:600;} QTabBar::tab:selected{color:#850D1C;border-bottom:2px solid #850D1C;}""")
        stage1_tab=QWidget();stage1_layout=QVBoxLayout(stage1_tab)
        stage1_layout.setContentsMargins(5,8,5,5)
        self.filter=QComboBox();self.filter.addItem('Semua');self.filter.currentTextChanged.connect(self.populate)
        stage1_layout.addWidget(self.filter)
        self.list=QTreeWidget();self.list.setHeaderHidden(True);self.list.itemClicked.connect(self.navigate_tree)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list.setToolTip('Centang field untuk memilih semua temuan di bawahnya. Centang sebagian = pilihan sebagian.')
        stage1_layout.addWidget(self.list,1)
        self.detail=QLabel('Pilih ketidaksesuaian untuk melihat detail.')
        self.detail.setWordWrap(True);self.detail.setMinimumHeight(90);stage1_layout.addWidget(self.detail)
        stage2_tab=QWidget();stage2_layout=QVBoxLayout(stage2_tab)
        stage2_layout.setContentsMargins(5,8,5,5)
        self.export_annotation_search=QLineEdit()
        self.export_annotation_search.setPlaceholderText('Cari parameter Tahap 2…')
        stage2_layout.addWidget(self.export_annotation_search)
        self.export_annotation_list=QListWidget()
        self.export_annotation_list.setMinimumHeight(160)
        stage2_layout.addWidget(self.export_annotation_list,1)
        self.export_annotation_search.textChanged.connect(self._filter_export_annotations)
        self.export_annotation_list.itemChanged.connect(self._export_annotation_toggled)
        info=QLabel('Centang = penanda muncul di PDF A/B dan ekspor.\nHapus centang = hanya menyembunyikan penanda, bukan menghapus hasil validasi.')
        info.setWordWrap(True);stage2_layout.addWidget(info)
        self.results_tabs.addTab(stage1_tab,'Tahap 1')
        self.results_tabs.addTab(stage2_tab,'Tahap 2')
        self.results_tabs.setTabToolTip(0,'Tahap 1 · Daftar Ketidaksesuaian')
        self.results_tabs.setTabToolTip(1,'Tahap 2 · Penanda')
        s.addWidget(self.results_tabs,1)
        # Validation remains reachable while the comparison stays in Step 2.
        self.inspector_validation_btn=QPushButton('Validasi Tahap 2…')
        self.inspector_validation_btn.clicked.connect(self.open_hybrid_validation)
        self.inspector_validation_btn.setEnabled(False)
        s.addWidget(self.inspector_validation_btn)
        self.hybrid_btn=QPushButton('▣  Manual Validation — Tahap 2')
        self.hybrid_btn.setObjectName('primary')
        self.hybrid_btn.clicked.connect(self.open_hybrid_validation)
        self.editor_btn=QPushButton('✎  Edit Hasil Koreksi');self.editor_btn.clicked.connect(self.open_editor)
        self.editor_text=None;self.editor_initial=None;self.editor_source=None;self.note_overrides={}
        self.apply_btn=QPushButton('Ekspor DOCX / Laporan Waybill');self.apply_btn.setObjectName('primary');self.apply_btn.clicked.connect(self.export_docx)
        self.notes_btn=QPushButton('Perbarui Preview Catatan');self.notes_btn.clicked.connect(lambda:self.correction_preview.refresh())
        self.pdf_btn=QPushButton('Ekspor Hasil Pemeriksaan PDF…');self.pdf_btn.clicked.connect(self.export_pdf)
        self.report_btn=QPushButton('Ekspor Laporan (JSON)');self.report_btn.clicked.connect(self.export_report)
        # Keep existing callbacks while presenting actions as a Word-style ribbon.
        def ribbon_group(title, buttons):
            group=QFrame();group.setObjectName('ribbonGroup')
            group_lay=QVBoxLayout(group);group_lay.setContentsMargins(2,0,2,0);group_lay.setSpacing(1)
            actions=QHBoxLayout();actions.setSpacing(4)
            for btn in buttons:
                btn.setMinimumHeight(30)
                btn.setMinimumWidth(96)
                btn.setSizePolicy(btn.sizePolicy().horizontalPolicy(), btn.sizePolicy().verticalPolicy())
                actions.addWidget(btn)
            group_lay.addLayout(actions)
            label=QLabel(title);label.setObjectName('ribbonCaption')
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            group_lay.addWidget(label)
            self.result_ribbon_layout.addWidget(group)
        # Short visible labels keep the toolbar compact on 1366px laptops.
        self.back_to_compare_btn=QPushButton('← Parameter & Bandingkan')
        self.back_to_compare_btn.clicked.connect(lambda:self.show_step(1))
        for button,label in ((self.back_to_compare_btn,'← Parameter & Bandingkan'),
                             (self.hybrid_btn,'Validasi Tahap 2'),
                             (self.editor_btn,'Edit Koreksi'),
                             (self.notes_btn,'Perbarui Catatan'),
                             (self.apply_btn,'Ekspor DOCX'),
                             (self.pdf_btn,'Ekspor PDF'),
                             (self.report_btn,'Ekspor JSON')):
            button.setToolTip(button.text())
            button.setText(label)
            button.setObjectName('ribbonAction')
        ribbon_group('NAVIGASI', [self.back_to_compare_btn])
        ribbon_group('VALIDASI', [self.hybrid_btn,self.editor_btn,self.notes_btn])
        ribbon_group('EKSPOR LAPORAN', [self.apply_btn,self.pdf_btn,self.report_btn])
        self.result_ribbon_layout.addStretch(1)
        split.addWidget(side)
        # Allow all three panels to shrink; preserve independent PDF scrolling.
        for viewer in (self.ref_view, self.exam_view):
            viewer.setMinimumWidth(0)
            viewer.scroll.setMinimumWidth(0)
            viewer.canvas.setMinimumWidth(240)
        side.setMinimumWidth(280)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(6)
        split.splitterMoved.connect(self._remember_inspector_width)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 1)
        # Step 2 keeps two synchronized document viewers and inspector;
        # Step 3 shows a SINGLE corrected-document page with editable margin notes.
        self.workspace_pages = QStackedWidget()
        self.workspace_pages.addWidget(split)
        self.correction_preview = CorrectionPreview(self)
        self.workspace_pages.addWidget(self.correction_preview)
        main.addWidget(self.workspace_pages, 1)
        from PySide6.QtWidgets import QApplication
        available=QApplication.primaryScreen().availableGeometry()
        width=min(1600, max(900, int(available.width()*0.98)))
        height=min(980, max(600, int(available.height()*0.94)))
        self.resize(min(width,available.width()),min(height,available.height()))
        self.move(available.x()+max(0,(available.width()-self.width())//2),
                  available.y()+max(0,(available.height()-self.height())//2))
        self.document_split.setSizes([540,540])
        split.setSizes(responsive_split_widths(self.width()-30,360))
        self.status=QLabel('v1.8.35.7 · Catatan rujukan & Auto ZIP Portable · Offline')
        main.addWidget(self.status)
        for button in (self.apply_btn,self.pdf_btn,self.report_btn,self.editor_btn,self.notes_btn,self.hybrid_btn,self.inspector_validation_btn):
            button.setEnabled(False)
        self.setStyleSheet(f'''QMainWindow,QWidget{{background:{BG};color:{DARK};font-family:Segoe UI,Arial;font-size:12px}}
          QPushButton{{background:white;border:1px solid #D8DADF;border-radius:6px;padding:6px 9px}}
          QPushButton#wizardStep{{padding:5px 9px;font-weight:600;min-height:32px}}
          QPushButton#ribbonAction{{padding:4px 8px;font-weight:600}}
          QPushButton:hover{{border-color:{RED};background:#FFF9FA}} QPushButton#primary{{background:{RED};color:white;border:0;font-weight:700;padding:7px 12px}}
          QFrame#resultRibbon{{background:#FFFFFF;border:1px solid #D9DEE5;border-radius:8px}}
          QFrame#ribbonGroup{{background:#FFFFFF;border-right:1px solid #E5E7EB}}
          QLabel#ribbonCaption{{background:#FFFFFF;color:#657080;font-size:9px}}
          QFrame#inspectorPane,QWidget#paperPanel{{background:#FFFFFF;border:1px solid #E1E5EA;border-radius:7px}}
          QLabel#sectionTitle{{background:#FFFFFF;color:{RED};font-weight:700}}
          QScrollArea#paperScroll{{border:1px solid #DDE2EA;background:#E9EDF2}}
          QListWidget,QComboBox{{background:white;border:1px solid #D8DADF;border-radius:6px;padding:6px}}
          QListWidget::item{{padding:8px;border-bottom:1px solid #EEEEEE}} QListWidget::item:selected{{background:#F6DCE0;color:#242424}}''')
    def _remember_inspector_width(self, position, index):
        """Respect user drag resizing instead of resetting it on every refresh."""
        if index == 1:
            widths = self.workspace_splitter.sizes()
            if len(widths) == 2 and widths[1] >= 180:
                self._preferred_inspector_width = widths[1]

    def _queue_workspace_fit(self):
        if not getattr(self, '_split_resize_queued', False):
            self._split_resize_queued=True
            QTimer.singleShot(0, self._fit_workspace_splitter)

    def _fit_workspace_splitter(self):
        self._split_resize_queued=False
        splitter=getattr(self, 'workspace_splitter', None)
        if splitter is None or splitter.width() <= 0:
            return
        current=splitter.sizes()
        wanted=responsive_split_widths(splitter.width(),
                    self._preferred_inspector_width, panel_min=280,
                    panel_max=480, documents_min=420)
        if len(current)==2 and abs(current[1]-wanted[1])>3:
            splitter.setSizes(wanted)
        # The panels must be allowed to scroll internally on smaller screens.

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'workspace_splitter'):
            self._queue_workspace_fit()

    def show_step(self,index):
        self.wizard_stack.setCurrentIndex(index)
        # The old empty third step occupied a large blank strip on screen.
        # Reclaim the entire area for the PDF viewers and the contextual ribbon.
        self.wizard_stack.setVisible(index != 2)
        if hasattr(self, 'result_ribbon'):
            self.result_ribbon.setVisible(index == 2)
        if hasattr(self, 'workspace_pages'):
            self.workspace_pages.setCurrentIndex(1 if index == 2 else 0)
        if index == 2 and hasattr(self, 'correction_preview'):
            # Defer rendering until the stacked page has its final viewport size.
            QTimer.singleShot(0, self.correction_preview.refresh)
        elif hasattr(self, 'ref_view'):
            QTimer.singleShot(0, self.ref_view.fit_width)
            QTimer.singleShot(0, self.exam_view.fit_width)
        if hasattr(self, 'results_tabs'):
            self.results_tabs.setCurrentIndex(0)
        if index != 2 and hasattr(self, 'workspace_splitter'):
            self._queue_workspace_fit()
        for i,button in enumerate(self.wizard_steps):
            button.setProperty('activeStep',i==index)
            button.setStyleSheet(
                'background:#850D1C;color:white;border:1px solid #850D1C;font-weight:700;' if i==index
                else 'background:white;color:#333;border:1px solid #D8DADF;font-weight:600;'
            )

    def reset_comparison(self):
        """Invalidate comparison artifacts whenever inputs or preset change."""
        self.diffs=[];self.reference=[];self.examined=[];self.reference_raw=[]
        self.has_compared=False
        self.ref_marks=[];self.exam_marks=[];self.ref_pages={};self.exam_pages={}
        self.active_scope=set();self.uncertain=[];self.rule_groups={}
        self.editor_text=None;self.editor_initial=None;self.editor_source=None
        self.note_overrides={};self._reference_profile_actual=None;self._reference_field_map={};self.waybill_mode=False;self.hybrid_stage2_records={};self.stage2_annotations={};self.stage2_visibility={};self._stage1_baseline=None;self.audit_events=[];self._session_file=None
        self.autosave_timer.stop()
        self.list.clear()
        self.detail.setText('Dokumen atau parameter berubah. Jalankan perbandingan baru.')
        for button in (self.apply_btn,self.pdf_btn,self.report_btn,self.editor_btn,self.notes_btn,self.hybrid_btn,self.inspector_validation_btn):
            button.setEnabled(False)

    def pick(self,side):
        name,_=QFileDialog.getOpenFileName(self,'Pilih dokumen','','Dokumen (*.docx *.pdf *.doc)')
        if not name:return
        path=Path(name)
        # Validate and render BEFORE changing the selected input. A failed
        # conversion must not leave a misleading filename on screen.
        try:
            preview_dir=self.work/('ref_preview' if side=='ref' else 'exam_preview')
            preview_dir.mkdir(parents=True,exist_ok=True)
            preview=make_preview(path,preview_dir)
            viewer=self.ref_view if side=='ref' else self.exam_view
            viewer.load(preview,[])
        except Exception as exc:
            QMessageBox.critical(self,'Dokumen tidak dapat dibuka',str(exc))
            return
        if side=='ref':
            self.ref_path=path;self.ref_btn.setText('Rujukan: '+path.name)
        else:
            self.exam_path=path;self.exam_btn.setText('Diperiksa: '+path.name)
        self.reset_comparison()
        # Preserve the newly loaded preview, but remove all previous markers.
        self.ref_view.marks=[];self.exam_view.marks=[]
        if self.ref_view.pdf:self.ref_view.render()
        if self.exam_view.pdf:self.exam_view.render()
        self.status.setText('Dokumen baru dimuat. Pilih parameter lalu klik Bandingkan Dokumen.')

    def mode_changed(self,*args):
        is_waybill=str(self.rule_mode.currentData()).startswith('waybill')
        self.scope_btn.setEnabled(not is_waybill)
        self.waybill_btn.setEnabled(is_waybill)
        if hasattr(self, 'reference_profile_bar'):
            self.reference_profile_bar.setVisible(is_waybill)
        if is_waybill:
            # Do not carry a field subset from another shipping-line template.
            selected_profile = self.rule_mode.currentData()
            if getattr(self, '_previous_waybill_preset', None) != selected_profile:
                self.waybill_fields = set(profile_field_names(selected_profile))
        self._previous_waybill_preset = self.rule_mode.currentData()
        self.all_scope.setEnabled(not is_waybill)
        if hasattr(self,'ref_view') and hasattr(self,'list'):
            self.reset_comparison()
            self.ref_view.marks=[];self.exam_view.marks=[]
            if self.ref_view.pdf:self.ref_view.render()
            if self.exam_view.pdf:self.exam_view.render()
            self.status.setText('Preset diubah. Jalankan perbandingan baru.')

    def choose_waybill(self):
        dlg=QDialog(self);dlg.setWindowTitle('Parameter Waybill');dlg.resize(540,600)
        layout=QVBoxLayout(dlg)
        layout.addWidget(QLabel('Pilih field berdasarkan SWB dokumen diperiksa (PDF B).\nDokumen rujukan (PDF A) boleh berupa surat/tabel berbeda layout jika label dan nilainya tersedia.'))
        items=QListWidget()
        for name in profile_field_names(self.rule_mode.currentData()):
            item=QListWidgetItem(name)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in self.waybill_fields or name not in {n for n,_ in FIELDS} else Qt.CheckState.Unchecked)
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
        self.reset_comparison()
        if not self.ref_path or not self.exam_path:QMessageBox.warning(self,'Berkas belum lengkap','Pilih kedua dokumen.');return
        try:
            self.waybill_mode=str(self.rule_mode.currentData()).startswith('waybill')
            if self.waybill_mode:
                if not self.waybill_fields:raise ValueError('Pilih minimal satu field Waybill.')
                a=self.work/'ref';b=self.work/'exam';a.mkdir(exist_ok=True);b.mkdir(exist_ok=True)
                refpdf=make_preview(self.ref_path,a);exampdf=make_preview(self.exam_path,b)
                self.diffs,locations=compare_waybills(
                    refpdf, exampdf,
                    self.waybill_fields & set(profile_field_names(self.rule_mode.currentData())),
                    profile=self.rule_mode.currentData(),
                    reference_profile=self.reference_profile_combo.currentData())
                self._reference_profile_actual = swb_rules.REFERENCE_EXTRACTION_DIAGNOSTICS.get(
                    'reference_profile', self.rule_mode.currentData())
                self._reference_field_map = dict(swb_rules.REFERENCE_EXTRACTION_DIAGNOSTICS.get('field_map', {}))
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
                self.populate();self.enable_results();self.show_step(1)
                a_profile = (PROFILE_LABELS.get(self._reference_profile_actual,
                             'Surat/tabel fleksibel' if self._reference_profile_actual == 'flexible'
                             else str(self._reference_profile_actual)))
                b_profile = PROFILE_LABELS.get(self.rule_mode.currentData(), self.rule_mode.currentText())
                self.status.setText(f'Rujukan A: {a_profile} → Diperiksa B: {b_profile} · {len(self.waybill_fields)} field · {len(self.diffs)} temuan.')
                if swb_rules.REFERENCE_NEEDS_REVIEW:
                    unresolved=sorted(set(swb_rules.REFERENCE_NEEDS_REVIEW))
                    self.status.setText(self.status.text() + f' · {len(unresolved)} field perlu verifikasi')
                    self.status.setToolTip('Tidak dapat dipastikan dari dokumen berlabel: ' + ', '.join(unresolved))
                ocr_message='Type3 decoder lokal; tidak membutuhkan OCR'
                if (self.rule_mode.currentData()=='waybill_gsl' and swb_rules.GSL_SKIPPED_FIELDS
                        and not swb_rules.REFERENCE_NEEDS_REVIEW):
                    self.status.setToolTip('Field GSL belum tervalidasi: ' + ', '.join(swb_rules.GSL_SKIPPED_FIELDS) + '. Field yang tidak dapat didekode perlu diverifikasi manual.')
                    self.status.setText(self.status.text() + f' · {len(swb_rules.GSL_SKIPPED_FIELDS)} field perlu verifikasi')
                if self.rule_mode.currentData()=='waybill_gsl':
                    import json
                    diag_path=self.work/'gsl_decoder_diagnostik.json'
                    diag_path.write_text(json.dumps({'ocr_status': ocr_message, 'field': swb_rules.GSL_DIAGNOSTICS, 'belum_tervalidasi': swb_rules.GSL_SKIPPED_FIELDS},ensure_ascii=False,indent=2,default=pdf_json_default),encoding='utf-8')
                    self.status.setToolTip('Diagnostik OCR disimpan: '+str(diag_path))
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
            self.ref_view.load(refpdf,self.ref_marks);self.exam_view.load(exampdf,self.exam_marks);self.populate();self.enable_results();self.show_step(1)
            self.status.setText(f'Cakupan {len(self.active_scope)}/{len(self.reference)} blok · {len(self.diffs)} perbedaan · {len(self.uncertain)} tidak terpetakan (perlu tinjauan) · Penanda {len(rm)}/{len(em)}.')
        except Exception as e:
            self.status.setText('Pemeriksaan gagal — tidak ada hasil baru yang dapat diekspor.')
            QMessageBox.critical(self,'Gagal',str(e))
    def enable_results(self):
        self.has_compared=True
        self._log_event('comparison_completed', {'findings':len(self.diffs), 'mode':self.rule_mode.currentData()})
        for button in (self.apply_btn,self.pdf_btn,self.report_btn,self.editor_btn,self.notes_btn,self.hybrid_btn,self.inspector_validation_btn):
            button.setEnabled(True)

    def _snapshot_stage1(self):
        """Immutable in-memory starting point for all Stage-2 promotions in one comparison."""
        if self._stage1_baseline is None:
            self._stage1_baseline = {
                'diffs': copy.deepcopy(self.diffs),
                'ref_marks': copy.deepcopy(self.ref_marks),
                'exam_marks': copy.deepcopy(self.exam_marks),
                'ref_pages': copy.deepcopy(self.ref_pages),
                'exam_pages': copy.deepcopy(self.exam_pages),
            }
        return self._stage1_baseline

    def _stage1_field_summary(self, fields):
        baseline = self._snapshot_stage1()
        result = {}
        for field in fields:
            differences = [d for d in baseline['diffs'] if getattr(d, 'field', None) == field]
            unreadable = self.waybill_mode and self.rule_mode.currentData() == 'waybill_gsl' and field in getattr(swb_rules, 'GSL_SKIPPED_FIELDS', [])
            result[field] = {
                'status': 'MISMATCH' if differences else ('PERLU_VERIFIKASI' if unreadable else 'MATCH'),
                'reference_text': '\n'.join(d.reference_text for d in differences if d.reference_text),
                'examined_text': '\n'.join(d.examined_text for d in differences if d.examined_text),
                'difference_count': len(differences),
            }
        return result

    def stage2_annotation_changed(self, field, checked, regions=None):
        """Share Stage-2 checkbox/coordinates with the Export preview and writers."""
        if not field:return
        self.stage2_visibility[field] = bool(checked)
        self._log_event('annotation_visibility', {'field':field, 'visible':bool(checked)})
        if regions:
            self.stage2_annotations[field] = copy.deepcopy(regions)
        self._refresh_export_annotations()
        self._refresh_main_annotation_previews()

    def _filter_export_annotations(self, text):
        if not hasattr(self, 'export_annotation_list'): return
        for i in range(self.export_annotation_list.count()):
            item = self.export_annotation_list.item(i)
            item.setHidden(text.casefold().strip() not in item.text().casefold())

    def _refresh_export_annotations(self):
        if not hasattr(self, 'export_annotation_list'):return
        items = self.export_annotation_list
        items.blockSignals(True)
        previous = self.export_annotation_search.text() if hasattr(self, 'export_annotation_search') else ''
        items.clear()
        for field in sorted(self.stage2_annotations, key=str.casefold):
            item = QListWidgetItem(field)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if self.stage2_visibility.get(field, True) else Qt.CheckState.Unchecked)
            items.addItem(item)
        items.blockSignals(False)
        self._filter_export_annotations(previous)

    def _export_annotation_toggled(self, item):
        self.stage2_visibility[item.text()] = item.checkState() == Qt.CheckState.Checked
        self._log_event('annotation_visibility', {'field':item.text(), 'visible':self.stage2_visibility[item.text()]})
        self._refresh_main_annotation_previews()

    def _visible_stage2_marks(self, side):
        out=[]
        side_key = 'A' if side == 'ref' else 'B'
        for field, parts in self.stage2_annotations.items():
            if not self.stage2_visibility.get(field, True):continue
            part = parts.get(side_key)
            if part and 'rect_pdf' in part:
                out.append({'field':field, 'page':int(part['page']), 'rect':fitz.Rect(part['rect_pdf'])})
        return out

    def _refresh_main_annotation_previews(self):
        for side, viewer in (('ref',self.ref_view),('exam',self.exam_view)):
            viewer.stage2_marks = self._visible_stage2_marks(side)
            viewer.mark_field_map = {i + 1: getattr(d, 'field', '') for i,d in enumerate(self.diffs)}
            viewer.hidden_stage2_fields = {f for f, checked in self.stage2_visibility.items() if not checked}
            if viewer.pdf:
                viewer.render()

    def apply_stage2_record(self, record):
        """Promote confirmed Waybill corrections into the active Stage-1 findings.

        Stage 1 baseline is retained; repeated edits rebuild from baseline, so no duplicate
        findings and removing a previous mismatch is deterministic. No PDF source is edited.
        """
        field = record['field_id']
        before = copy.deepcopy(self.hybrid_stage2_records.get(field))
        self.hybrid_stage2_records[field] = copy.deepcopy(record)
        self._log_event('stage2_confirm', {'field':field, 'previous':before, 'current':record})
        baseline = self._snapshot_stage1()
        if not self.waybill_mode:
            # General document comparison is paragraph/index based; a name-based field
            # replacement here would corrupt alignment. Keep audit until mapped safely.
            self.status.setText(f'{field}: verifikasi tersimpan. Sinkronisasi daftar temuan hanya tersedia untuk mode Waybill.')
            return
        removals = {
            name for name, entry in self.hybrid_stage2_records.items()
            if entry.get('outcome') == 'override_stage1' and entry.get('status') in ('MATCH', 'MISMATCH', 'PERLU_VERIFIKASI')
        }
        original = baseline['diffs']
        retained = [(i, copy.deepcopy(d)) for i,d in enumerate(original, 1)
                    if getattr(d, 'field', '') not in removals]
        idmap = {old_id: new_id for new_id,(old_id,_) in enumerate(retained,1)}
        self.diffs = [d for _,d in retained]
        self.ref_marks = [{**copy.deepcopy(m), 'id': idmap[m['id']]}
                          for m in baseline['ref_marks'] if m['id'] in idmap]
        self.exam_marks = [{**copy.deepcopy(m), 'id': idmap[m['id']]}
                          for m in baseline['exam_marks'] if m['id'] in idmap]
        self.ref_pages = {idmap[i]: page for i,page in baseline['ref_pages'].items() if i in idmap}
        self.exam_pages = {idmap[i]: page for i,page in baseline['exam_pages'].items() if i in idmap}
        for name, entry in self.hybrid_stage2_records.items():
            if name not in removals or entry.get('status') not in ('MISMATCH', 'PERLU_VERIFIKASI'):
                continue
            a,b = entry.get('A'),entry.get('B')
            if not a or not b: continue
            i = len(self.diffs)+1
            finding_kind = ('Perlu Verifikasi' if entry.get('status') == 'PERLU_VERIFIKASI' else 'Perubahan')
            self.diffs.append(WaybillDifference(finding_kind, None, None,
                a.get('text_final',''), b.get('text_final',''),
                f'Field Waybill: {name}; diverifikasi ulang Tahap 2', False, name))
            for part, marks, pages, side in (
                (a,self.ref_marks,self.ref_pages,'ref'),(b,self.exam_marks,self.exam_pages,'exam')):
                page = int(part['page'])
                rect = fitz.Rect(part['rect_pdf'])
                marks.append({'id':i,'page':page,'rect':rect,'side':side,'kind':finding_kind})
                pages[i] = page
        self.sort_differences()
        self.populate()
        # Re-render annotated pages from active findings. Existing source PDFs stay immutable.
        if self.ref_view.pdf and self.exam_view.pdf:
            self.ref_view.load(self.ref_view.pdf.name, self.ref_marks)
            self.exam_view.load(self.exam_view.pdf.name, self.exam_marks)
            self._refresh_main_annotation_previews()
        self.status.setText(f'Tahap 2 diterapkan: {field} · {len(self.diffs)} temuan aktif · '
            f'{len(self.hybrid_stage2_records)} parameter diverifikasi. Baseline Tahap 1 tersimpan.')

    def open_hybrid_validation(self):
        """Continue stage-one results with an optional editable second-stage review."""
        if not self.ref_view.pdf or not self.exam_view.pdf:
            QMessageBox.warning(self,'Dokumen belum dibandingkan',
                'Jalankan Bandingkan Dokumen terlebih dahulu.')
            return
        if self.waybill_mode:
            profile=str(self.rule_mode.currentData())
            fields=profile_field_names(profile)
        else:
            profile=''
            fields=sorted({getattr(d,'field','') for d in self.diffs if getattr(d,'field','')})
            if not fields:
                fields=[f'Parameter {i+1}' for i in range(max(1,len(self.diffs)))]
        stage1 = self._stage1_field_summary(fields)
        dlg=HybridValidationDialog(self.ref_view.pdf.name,self.exam_view.pdf.name,
                                   fields,profile,self,stage1_fields=stage1)
        dlg.records=copy.deepcopy(self.hybrid_stage2_records)
        dlg.annotation_regions=copy.deepcopy(self.stage2_annotations)
        dlg.annotation_visibility.update(self.stage2_visibility)
        dlg.field_list.blockSignals(True)
        for i in range(dlg.field_list.count()):
            item = dlg.field_list.item(i)
            item.setCheckState(Qt.CheckState.Checked if dlg.annotation_visibility.get(item.text(),True) else Qt.CheckState.Unchecked)
        dlg.field_list.blockSignals(False)
        dlg._refresh_persistent_overlays()
        dlg._refresh_checklist()
        if dlg.records and dlg.field_list.currentItem():
            dlg.change_field(dlg.field_list.currentItem().text())
        dlg.exec()
        self.hybrid_stage2_records.update(copy.deepcopy(dlg.records))
        self.stage2_annotations.update(copy.deepcopy(dlg.annotation_regions))
        self.stage2_visibility.update(dlg.annotation_visibility)
        self._refresh_export_annotations()
        self._refresh_main_annotation_previews()
        self._log_event('stage2_dialog_closed', {'record_count':len(self.hybrid_stage2_records)})
        self.status.setText(self.status.text().split(' · Tahap 2:')[0] +
            f' · Tahap 2: {len(self.hybrid_stage2_records)} parameter diverifikasi')

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
        # Show only discrepancy categories that actually exist in current findings.
        categories = sorted({str(d.kind) for d in self.diffs if getattr(d,'kind',None)},
                            key=lambda k: (['Perubahan','Hilang','Berlebih','Perlu Verifikasi'].index(k)
                                           if k in ('Perubahan','Hilang','Berlebih','Perlu Verifikasi') else 99,k))
        previous_filter=self.filter.currentText()
        desired=['Semua'] + categories
        if [self.filter.itemText(i) for i in range(self.filter.count())] != desired:
            self.filter.blockSignals(True)
            self.filter.clear();self.filter.addItems(desired)
            self.filter.setCurrentText(previous_filter if previous_filter in desired else 'Semua')
            self.filter.blockSignals(False)
        current_filter=self.filter.currentText()
        self.visible=[]
        if self.waybill_mode:
            groups={}
            for i,d in enumerate(self.diffs):
                if current_filter != 'Semua' and d.kind != current_filter:continue
                groups.setdefault(d.field or 'Lainnya',[]).append((i,d))
            for field,entries in groups.items():
                kinds={k:sum(d.kind==k for _,d in entries) for k in categories}
                summary=' · '.join(f'{count} {kind}' for kind,count in kinds.items() if count)
                parent=QTreeWidgetItem([f'{field}  ({len(entries)} temuan)  ·  {summary}'])
                parent.setData(0, Qt.ItemDataRole.UserRole, ('field', field))
                parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                parent.setToolTip(0, f'Centang untuk memilih semua {len(entries)} temuan pada {field}')
                self.list.addTopLevelItem(parent)
                for i,d in entries:
                    snippet=(d.examined_text or d.reference_text).replace('\n',' ')[:85]
                    label=f'#{i+1} · {d.kind}  —  {snippet}'
                    item=QTreeWidgetItem([label])
                    item.setData(0,Qt.ItemDataRole.UserRole,i)
                    item.setToolTip(0, f'#{i+1} · {d.kind} — {d.examined_text or d.reference_text}')
                    item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
                    parent.addChild(item)
                    item.setCheckState(0,Qt.CheckState.Checked if d.apply else Qt.CheckState.Unchecked)
                parent.setCheckState(0, Qt.CheckState(group_check_state(d.apply for _,d in entries)))
                parent.setExpanded(True)
        else:
            for i,d in enumerate(self.diffs):
                if current_filter != 'Semua' and d.kind != current_filter:continue
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
        data=item.data(0,Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and data and data[0]=='field':
            checked=item.checkState(0)!=Qt.CheckState.Unchecked
            self.list.blockSignals(True)
            updated=[]
            try:
                for j in range(item.childCount()):
                    child=item.child(j)
                    index=child.data(0,Qt.ItemDataRole.UserRole)
                    if not isinstance(index,int) or index>=len(self.diffs):continue
                    child.setCheckState(0,Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                    if self.diffs[index].apply != checked:
                        self.diffs[index].apply=checked
                        updated.append(index)
                item.setCheckState(0,Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            finally:
                self.list.blockSignals(False)
            if updated:
                self._log_event('field_toggle', {'field':data[1], 'indices':updated, 'apply':checked})
        elif isinstance(data,int) and 0<=data<len(self.diffs):
            checked=item.checkState(0)==Qt.CheckState.Checked
            self.diffs[data].apply=checked
            parent=item.parent()
            if parent is not None:
                states=[parent.child(i).checkState(0)==Qt.CheckState.Checked for i in range(parent.childCount())]
                self.list.blockSignals(True)
                try:
                    parent.setCheckState(0,Qt.CheckState(group_check_state(states)))
                finally:
                    self.list.blockSignals(False)
            self._log_event('finding_toggle', {'index':data, 'apply':checked})
        else:
            return
        if self.editor_text is not None:
            self.status.setText('Pilihan koreksi berubah. Editor sebelumnya tetap tersimpan; buka Editor untuk meninjaunya.')
    def navigate_tree(self,item,column):
        index=item.data(0,Qt.ItemDataRole.UserRole)
        if not isinstance(index,int):
            # The disclosure arrow controls expansion; clicks on the parent
            # should not unexpectedly collapse all of its findings.
            return
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
                # If a Stage-2 field is unchecked in Hasil & Ekspor, hide its
                # Stage-1 mark as well so all markings obey the same switch.
                mid = mark.get('id', 0)
                if 1 <= mid <= len(self.diffs):
                    field = getattr(self.diffs[mid - 1], 'field', '')
                    if field in self.stage2_visibility and not self.stage2_visibility[field]:
                        continue
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
            # Export selected second-stage rectangles as vector annotations.
            for mark in self._visible_stage2_marks(side):
                pno = mark['page']
                if pno < 0 or pno >= len(output):continue
                rect = fitz.Rect(mark['rect']) & output[pno].rect
                if rect.is_empty or rect.is_infinite:continue
                shape = output[pno].new_shape()
                shape.draw_rect(rect)
                shape.finish(color=(0.09, 0.42, 0.63), fill=(0.09, 0.42, 0.63),
                             fill_opacity=0.10, stroke_opacity=0.85, width=0.8)
                shape.commit(overlay=True)
                # Sticky correction note, only for an explicitly confirmed override;
                # unconfirmed batch coordinates are merely visual candidates.
                record = self.hybrid_stage2_records.get(mark['field'], {})
                if record.get('outcome') == 'override_stage1':
                    original = record.get('A', {}).get('text_final', '')
                    examined = record.get('B', {}).get('text_final', '')
                    if original != examined or record.get('status') == 'PERLU_VERIFIKASI':
                        note = ('DocMatch Tahap 2 | ' + mark['field'] + '\n'
                                + 'Rujukan: ' + original[:500] + '\n'
                                + 'Diperiksa: ' + examined[:500])
                        pos = fitz.Point(min(rect.x1 + 3, output[pno].rect.x1 - 12),
                                         min(max(12, rect.y0), output[pno].rect.y1 - 12))
                        try:
                            output[pno].add_text_annot(pos, note)
                        except (ValueError, RuntimeError):
                            pass
            meta = dict(output.metadata or {})
            meta['subject'] = 'DocMatch Waybill - salinan audit beranotasi, bukan koreksi otomatis'
            output.set_metadata(meta)
            output.save(str(target), garbage=3, deflate=True)

    def choose_pdf_export_documents(self):
        """Choose any combination of the four PDF output types."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Ekspor Hasil Pemeriksaan PDF — Termasuk Anotasi Tahap 2')
        dialog.resize(590, 350)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Pilih satu atau beberapa dokumen untuk diekspor:'))
        choices = [
            ('ref', 'Dokumen Rujukan — PDF beranotasi'),
            ('exam', 'Dokumen Diperiksa — PDF beranotasi'),
            ('corrected', 'Hasil Koreksi Bersih — penggantian teks yang disetujui'),
            ('notes', 'Hasil Koreksi dengan Catatan — stabilo dan catatan di margin kanan'),
        ]
        approved = [(i + 1, d) for i, d in enumerate(self.diffs) if d.apply]
        # Margin-note export needs approved Stage-1 findings with positioned marks.
        approved_ids = {i for i, _ in approved}
        review_active = (hasattr(self, 'workspace_pages') and
                         self.workspace_pages.currentIndex() == 1)
        include_all_preview_notes = (review_active and hasattr(self, 'correction_preview') and
                                     self.correction_preview.all_notes.isChecked())
        available_ids = ({i + 1 for i in range(len(self.diffs))} if include_all_preview_notes
                         else approved_ids)
        has_positioned_notes = any(m.get('id') in available_ids for m in self.exam_marks)
        # The 'clean correction' writer additionally requires strict, one-word substitutions.
        def safe_clean(i, diff):
            hits = [m for m in self.exam_marks if m.get('id') == i]
            if diff.kind != 'Perubahan' or len(hits) != 1:
                return False
            old, new = diff.examined_text.strip(), diff.reference_text.strip()
            if not old or not new or len(old.split()) != 1 or len(new.split()) != 1:
                return False
            try:
                mark = hits[0]
                page = self.exam_view.pdf[mark['page']]
                rect = fitz.Rect(mark['rect'])
                return bool(page.get_textbox(rect).strip() == old and rect.width >= 8 and rect.height >= 4)
            except (ValueError, IndexError, KeyError, RuntimeError):
                return False
        can_clean = bool(approved) and all(safe_clean(i, d) for i, d in approved)
        boxes = []
        for key, label in choices:
            cb = QCheckBox(label)
            cb.setChecked(key == 'notes' if review_active and has_positioned_notes else key in ('ref', 'exam'))
            if key == 'notes' and not has_positioned_notes:
                cb.setEnabled(False)
                cb.setToolTip('Perlu minimal satu temuan Tahap 1 dicentang dan memiliki posisi.')
            if key == 'corrected' and not can_clean:
                cb.setEnabled(False)
                cb.setToolTip('Koreksi bersih hanya tersedia untuk penggantian teks yang sudah disetujui dan aman.')
            layout.addWidget(cb)
            boxes.append((key, cb))
        row = QHBoxLayout()
        all_btn = QPushButton('Pilih Semua')
        none_btn = QPushButton('Hapus Semua')
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for _, cb in boxes if cb.isEnabled()])
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
        selected = [key for key, cb in boxes if cb.isChecked() and cb.isEnabled()]
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
                                    diff.examined_text, diff.reference_text, diff.kind, getattr(diff, 'field', ''))

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
        working = dict(self.note_overrides)
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
            # Re-render using the SAME PDF writer as export: numbered
            # highlights and note cards, without connecting lines.
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
            page_groups = [g for g in self.grouped_correction_notes() if g['page'] == page_no]
            keys = [g['key'] for g in page_groups]
            if len(note_rects) != len(keys):
                # Never silently connect an editor to the wrong correction.
                raise ValueError('Tidak dapat mencocokkan kotak catatan dengan temuan. '
                                 'Gunakan editor daftar untuk dokumen ini.')
            for group, rect in zip(page_groups, note_rects):
                key = group['key']
                editor = QPlainTextEdit(canvas)
                editor.setPlainText(working.get(key, group['text']))
                editor.setToolTip(f'Catatan {group["field"]} — ketik untuk mengubah')
                editor.setStyleSheet('QPlainTextEdit { background: #FFF9F6; color: #850D1C; '
                                     'border: 1px solid #BD8A91; font: italic 12px Arial; '
                                     'padding: 3px; } QPlainTextEdit:focus { border: 2px solid #850D1C; }')
                x = round((rect.x0 + 4) * zoom)
                y = round((rect.y0 + 17) * zoom)
                w = max(85, round((rect.width - 8) * zoom))
                h = max(26, round((rect.height - 20) * zoom))
                editor.setGeometry(x, y, w, h)
                editor.show()
                state['editors'].append((key, editor))
            page_label.setText(f'Halaman {page_no+1} / {len(pdf)} · {len(keys)} kotak field dapat diedit')
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
                correction_pdf_filename(self.exam_path), 'PDF (*.pdf)')
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
            filename, _ = QFileDialog.getSaveFileName(dialog, 'Ekspor PDF catatan yang diedit', correction_pdf_filename(self.exam_path), 'PDF (*.pdf)')
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

    @staticmethod
    def _gsl_field_lines(words):
        """Rebuild full reference content from OCR word positions, not diff snippets."""
        if not words:
            return ''
        ordered = sorted(words, key=lambda w: (int(w.get('page', 0)), float(w['rect'].y0), float(w['rect'].x0)))
        lines = []
        for w in ordered:
            r = fitz.Rect(w['rect'])
            if not lines or w.get('page', 0) != lines[-1]['page'] or abs(r.y0 - lines[-1]['y']) > max(3.5, min(9, r.height * .65)):
                lines.append({'page': w.get('page', 0), 'y': r.y0, 'words': [w]})
            else:
                lines[-1]['words'].append(w)
        return '\n'.join(' '.join(str(w['word']) for w in sorted(line['words'], key=lambda v: v['rect'].x0)) for line in lines).strip()

    @staticmethod
    def _gsl_change_explanation(reference, examined):
        """Describe verifiable token changes; avoid guessing semantic categories."""
        def tokens(t):
            return re.findall(r'\S+', t)
        a, b = tokens(examined), tokens(reference)
        matcher = difflib.SequenceMatcher(None, [x.casefold() for x in a], [x.casefold() for x in b], autojunk=False)
        changes = []
        for op, i, j, k, l in matcher.get_opcodes():
            if op == 'equal':
                continue
            old, new = ' '.join(a[i:j]), ' '.join(b[k:l])
            if op == 'replace':
                changes.append(f'Ganti "{old}" menjadi "{new}"')
            elif op == 'delete':
                changes.append(f'Hapus "{old}"')
            else:
                changes.append(f'Tambahkan "{new}"')
        if not changes:
            return 'Tidak ada perbedaan teks yang terkonfirmasi setelah normalisasi OCR.'
        if len(changes) > 8:
            return '; '.join(changes[:8]) + f'; dan {len(changes)-8} perubahan lainnya.'
        return '; '.join(changes) + '.'

    @staticmethod
    def _gsl_page_one_box(page, field):
        """Printed cell outline, not an OCR word rectangle."""
        regions = swb_rules.GSL_CELLS.get(field, [])
        if not regions or regions[0][0] != 0:
            return None
        _, x0, y0, x1, y1 = regions[0]
        r = page.rect
        return fitz.Rect(r.x0 + x0*r.width, r.y0 + y0*r.height,
                         r.x0 + x1*r.width, r.y0 + y1*r.height)

    @staticmethod
    def _gsl_precise_outline(page, field, printed):
        """Outline recovered value glyphs, never the complete template cell.

        Use the examined-document glyph coordinates, not the reference document
        or the entire field region. Clamp to the field interior so Type3 glyph
        geometry cannot spill into adjacent printed cells.
        """
        record = swb_rules.GSL_DIAGNOSTICS.get(field, {})
        exam = record.get('diperiksa', {})
        if not exam.get('valid') or not exam.get('words'):
            return None
        # Reserve a small header strip for the template label (e.g. BOOKING No.).
        content = fitz.Rect(printed.x0 + 1.0, printed.y0 + min(9.0, printed.height * .30),
                            printed.x1 - 1.0, printed.y1 - 1.0)
        if content.is_empty:
            return None
        boxes = []
        for word in exam['words']:
            if int(word.get('page', 0)) != 0:
                continue
            r = fitz.Rect(word['rect'])
            if not all(__import__("math").isfinite(v) for v in (r.x0, r.y0, r.x1, r.y1)) or r.is_empty:
                continue
            mid = (r.tl + r.br) * .5
            if not content.contains(mid):
                continue
            clipped = r & content
            if not clipped.is_empty:
                boxes.append(clipped)
        if not boxes:
            return None
        result = fitz.Rect(boxes[0])
        for r in boxes[1:]:
            result |= r
        # Tight optical padding; never exceed the printed cell boundary.
        result = fitz.Rect(result.x0 - 1.5, result.y0 - 1.5,
                           result.x1 + 1.5, result.y1 + 1.5) & printed
        return result if not result.is_empty else None

    def grouped_correction_notes(self, include_unchecked=False):
        """One note per PDF page and field, with full GSL reference and change details."""
        # Local import also keeps the isolated method's legacy regression tests
        # compatible, without adding any dependencies to the old note editor.
        from reference_note_format import structured_reference_values, is_structured_field
        approved = {i + 1: d for i, d in enumerate(self.diffs) if d.apply or include_unchecked}
        grouped = {}
        for mark in self.exam_marks:
            n = mark.get('id')
            if n not in approved:
                continue
            d = approved[n]
            field = (getattr(d, 'field', '') or 'Lainnya').strip()
            key = (mark['page'], field.casefold())
            item = grouped.setdefault(key, {'page': mark['page'], 'field': field,
                                            'numbers': [], 'rectangles': [], 'kinds': []})
            if n not in item['numbers']:
                item['numbers'].append(n)
            if str(d.kind) not in item['kinds']:
                item['kinds'].append(str(d.kind))
            item['rectangles'].append(fitz.Rect(mark['rect']))
        # Catatan untuk Shipper/Consignee/Notify Party wajib mengambil seluruh
        # isi field dari dokumen A, bukan potongan kata dari hasil diff.
        # Satu ekstraksi per preview menjaga performa dan huruf/spasi/baris.
        address_fields = {item['field'] for item in grouped.values()
                          if is_address_field(item['field'])}
        address_source = getattr(getattr(self, 'ref_view', None), 'pdf', None)
        source_path = getattr(address_source, 'name', None) or getattr(self, 'ref_path', None)
        profile = getattr(self, '_reference_profile_actual', None) or self.rule_mode.currentData()
        # Flexible letters need the examined field vocabulary as stop labels;
        # carrier SWBs use the independently detected source carrier's labels.
        note_profile = self.rule_mode.currentData() if profile == 'flexible' else profile
        note_field_map = getattr(self, '_reference_field_map', None) or None
        reference_values = (address_reference_values(source_path, note_profile, address_fields,
                                                     field_map=note_field_map)
                            if address_fields else {})
        # v1.8.35.6: Cargo/weight notes use the same independent PDF A, but keep its
        # visually aligned rows. No change to the comparison/marker engine.
        structured_fields = {item['field'] for item in grouped.values()
                             if is_structured_field(item['field'])}
        if structured_fields:
            reference_values.update(structured_reference_values(
                source_path, note_profile, structured_fields, field_map=note_field_map))
        result = []
        for item in grouped.values():
            item['numbers'].sort()
            group_key = f'group:{item["page"]}:{item["field"].casefold()}'
            item['key'] = group_key
            notes = []
            for n in item['numbers']:
                value = (self.note_overrides.get(n, self.default_correction_note(n)) or '').strip()
                if not value:
                    value = '[HAPUS TEKS BERLEBIH]'
                prefix = item['field'] + ':'
                if value.casefold().startswith(prefix.casefold()):
                    value = value[len(prefix):].strip()
                if value and value not in notes:
                    notes.append(value)
            default = '\n'.join(notes)
            if (self.waybill_mode and self.rule_mode.currentData() == 'waybill_gsl'
                    and item['page'] == 0):
                record = swb_rules.GSL_DIAGNOSTICS.get(item['field'], {})
                ref = record.get('rujukan', {})
                exam = record.get('diperiksa', {})
                if ref.get('valid') and exam.get('valid'):
                    ref_text = self._gsl_field_lines(ref['words'])
                    exam_text = self._gsl_field_lines(exam['words'])
                    if ref_text:
                        default = ref_text
                else:
                    default = ('[VERIFIKASI MANUAL DIPERLUKAN: OCR field belum tervalidasi]\n' + default)
            # Complete source-faithful field text for addresses and cargo,
            # including original case, line breaks, numbers and units. Never
            # override individual/manual edits or unverified field extraction.
            if ((is_address_field(item['field']) or is_structured_field(item['field']))
                    and item['field'] in reference_values
                    and not any(n in self.note_overrides for n in item['numbers'])):
                default = reference_values[item['field']]
            # Group-level user edits take precedence over generated reference text.
            item['text'] = self.note_overrides.get(group_key, default)
            if (self.waybill_mode and self.rule_mode.currentData() == 'waybill_gsl'
                    and not is_address_field(item['field'])
                    and not is_structured_field(item['field'])):
                item['text'] = re.sub(r'^\s*KOREKSI SESUAI RUJUKAN\s*:\s*\n?', '', item['text'], flags=re.IGNORECASE)
                item['text'] = re.split(r'\n\s*PENJELASAN PERUBAHAN\s*:', item['text'], maxsplit=1, flags=re.IGNORECASE)[0].strip()
            item['anchor'] = min(item['rectangles'], key=lambda r: (r.y0, r.x0))
            if (self.waybill_mode and self.rule_mode.currentData() == 'waybill_gsl'
                    and item['page'] == 0 and self.exam_view.pdf):
                printed = self._gsl_page_one_box(self.exam_view.pdf[0], item['field'])
                if printed is not None:
                    precise = self._gsl_precise_outline(self.exam_view.pdf[0], item['field'], printed)
                    # An unverified glyph box must not be represented as a precise
                    # correction. Fall back to the original cell outline.
                    item['outline'] = precise if precise is not None else printed
                    item['anchor'] = item['outline']
            result.append(item)
        return sorted(result, key=lambda item: (item['page'], item['anchor'].y0, item['anchor'].x0))

    def export_waybill_notes_pdf(self, target, *, include_unchecked=False, allow_empty=False):
        """Numbered highlights without connector lines; original margin note editors."""
        if not self.exam_view.pdf:
            raise ValueError('PDF dokumen diperiksa belum tersedia.')
        if not allow_empty and not any(d.apply for d in self.diffs) and not include_unchecked:
            raise ValueError('Belum ada temuan yang dipilih.')
        notes = self.grouped_correction_notes(include_unchecked=include_unchecked)
        if not allow_empty and not notes:
            raise ValueError('Temuan terpilih tidak memiliki posisi stabilo pada PDF diperiksa.')
        source = self.exam_view.pdf
        margin = NOTE_MARGIN

        with fitz.open() as output:
            for pno, original in enumerate(source):
                bounds = original.rect
                page_height, measured = note_box_layout(notes, pno,
                                                         bounds.width, bounds.height,
                                                         margin=margin)
                page_notes = [item for item, _, _ in measured]
                page = output.new_page(width=bounds.width + margin, height=page_height)
                page.show_pdf_page(fitz.Rect(0, 0, bounds.width, bounds.height), source, pno)
                # On GSL's first page, changed data is shown by a single
                # red outline around the whole printed cell, never word highlights.
                gsl_first = (self.waybill_mode and
                             self.rule_mode.currentData() == 'waybill_gsl' and pno == 0)
                if gsl_first:
                    for item in page_notes:
                        outline = item.get('outline')
                        if outline is not None:
                            page.draw_rect(outline, color=(0.77, 0.05, 0.14), width=1.8)
                else:
                    for mark in (m for m in self.exam_marks
                                 if m['page'] == pno and m.get('id') in
                                 {num for item in page_notes for num in item['numbers']}):
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
                if not measured:
                    continue
                page.insert_text((bounds.width + 17, 26), 'CATATAN KOREKSI',
                                 fontname='hebo', fontsize=10, color=(0.50, 0.05, 0.12))
                # Work in source PDF coordinates. Reserve every word/value
                # and all highlighted regions before placing any numbered badge.
                # This avoids a marker for Quantity covering Cargo or a Seal.
                text_boxes = [fitz.Rect(w[:4]) for w in original.get_text('words')]
                protected = [fitz.Rect(m['rect']) for m in self.exam_marks
                             if m['page'] == pno and m.get('id') in
                             {number for item in page_notes for number in item['numbers']}]
                protected += [fitz.Rect(item['outline']) for item in page_notes
                              if item.get('outline') is not None]
                placed_badges = []
                # A raster-only/Type3 form might have no usable word layer.
                # Check ink on the *original* page in that case to avoid
                # obscuring characters that exist only as page graphics.
                ink_guard = scan_ink_guard(original) if (gsl_first or not text_boxes) else None
                for item, lines, rect in measured:
                    x0, top = rect.x0, rect.y0
                    page.draw_rect(rect, color=(0.72, 0.52, 0.54),
                                   fill=(1, 0.98, 0.96), width=0.6)
                    numbers = item['numbers']
                    label = (f'#{numbers[0]:02d}' if len(numbers) == 1 else
                             f'#{numbers[0]:02d}-#{numbers[-1]:02d}')
                    status = ' / '.join(item.get('kinds', ['Perubahan']))
                    header = f'{label}  {status} - {item["field"]}'
                    # Shorten only the header if needed, never the correction itself.
                    while (len(header) > 1 and
                           fitz.get_text_length(header, fontname='hebo', fontsize=8) > rect.width - 12):
                        header = header[:-1]
                    page.insert_text((x0 + 6, top + 12), header,
                                     fontname='hebo', fontsize=8, color=(0.48, 0.05, 0.11))
                    text_rect = fitz.Rect(x0 + 6, top + 21, rect.x1 - 6, rect.y1 - 5)
                    if page.insert_textbox(text_rect, '\n'.join(lines), fontname='heit',
                                           fontsize=9.5, lineheight=1.18,
                                           color=(0.35, 0.06, 0.13)) < 0:
                        raise ValueError(f'Catatan field {item["field"]} tidak muat.')
                    # A compact matching badge sits beside the highlighted PDF value.
                    # Do not draw leader/connector lines; they become unreadable
                    # when a document has many corrections.
                    anchor = item.get('outline', item['anchor'])
                    draw_number_marker(page, anchor, item['numbers'],
                                       bounds.width, bounds.height,
                                       text_boxes=text_boxes,
                                       occupied=placed_badges,
                                       protected=protected,
                                       ink_guard=ink_guard)
            meta = dict(output.metadata or {})
            meta['subject'] = ('DocMatch - PDF diperiksa dengan catatan per field; '
                               'teks asli tidak diubah')
            output.set_metadata(meta)
            output.save(str(target), garbage=3, deflate=True)

    def export_waybill_docx(self,target):
        # Build a cleaner Word-style report: a readable audit document first,
        # then the visual appendix. The source PDF itself is never modified.
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

        doc = Document()
        section = doc.sections[0]
        section.top_margin = Inches(.6)
        section.bottom_margin = Inches(.6)
        section.left_margin = Inches(.75)
        section.right_margin = Inches(.75)

        styles = doc.styles
        styles['Normal'].font.name = 'Calibri'
        styles['Normal'].font.size = Pt(11)

        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run('DocMatch — Laporan Pemeriksaan Waybill')
        run.bold = True
        run.font.size = Pt(16)

        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.add_run('Ringkasan hasil pembandingan dan validasi dokumen').italic = True

        meta = doc.add_table(rows=4, cols=2)
        meta.style = 'Table Grid'
        meta.alignment = WD_TABLE_ALIGNMENT.CENTER
        metadata = [
            ('Dokumen rujukan', str(self.ref_path.name if self.ref_path else '-')),
            ('Dokumen diperiksa', str(self.exam_path.name if self.exam_path else '-')),
            ('Jumlah temuan', str(len(self.diffs))),
            ('Keterangan', 'Laporan ini bersifat audit. Dokumen asli tidak diubah oleh DocMatch.'),
        ]
        for row, (label, value) in zip(meta.rows, metadata):
            row.cells[0].text = label
            row.cells[1].text = value
            for idx, cell in enumerate(row.cells):
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                if idx == 0:
                    for p in cell.paragraphs:
                        for r in p.runs:
                            r.bold = True

        doc.add_paragraph('')
        heading = doc.add_paragraph()
        heading_run = heading.add_run('Daftar Temuan')
        heading_run.bold = True
        heading_run.font.size = Pt(13)

        intro = doc.add_paragraph(
            'Tabel berikut merangkum perbedaan utama antara dokumen rujukan dan dokumen diperiksa. '
            'Kolom teks dapat ditinjau dan disunting bila diperlukan untuk keperluan administrasi internal.'
        )

        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ['No.', 'Field', 'Kategori', 'Rujukan', 'Diperiksa']
        for cell, label in zip(table.rows[0].cells, headers):
            cell.text = label
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cell.paragraphs:
                for r in p.runs:
                    r.bold = True

        if self.diffs:
            for i, d in enumerate(self.diffs, 1):
                row = table.add_row()
                values = [
                    str(i),
                    str(getattr(d, 'field', '')),
                    str(d.kind),
                    str(d.reference_text),
                    str(d.examined_text),
                ]
                for cell, value in zip(row.cells, values):
                    cell.text = value
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        else:
            row = table.add_row()
            row.cells[0].merge(row.cells[-1])
            row.cells[0].text = 'Tidak ada temuan yang tercatat pada sesi ini.'

        if not self.exam_view.pdf:
            doc.save(str(target))
            return

        doc.add_page_break()
        appendix = doc.add_paragraph()
        appendix_run = appendix.add_run('Lampiran Visual')
        appendix_run.bold = True
        appendix_run.font.size = Pt(13)
        doc.add_paragraph('Halaman berikut menampilkan salinan visual dokumen diperiksa yang telah diberi penanda anotasi.')

        pdf = self.exam_view.pdf
        usable = section.page_width - section.left_margin - section.right_margin
        for pno, page in enumerate(pdf):
            page_title = doc.add_paragraph()
            page_title_run = page_title.add_run(f'Halaman {pno + 1}')
            page_title_run.bold = True
            with fitz.open() as one:
                one.insert_pdf(pdf, from_page=pno, to_page=pno)
                for mark in self.exam_marks:
                    if mark['page'] != pno:
                        continue
                    rect = fitz.Rect(mark['rect'])
                    kind = mark.get('kind', 'Perubahan')
                    rgb = {'Perubahan': (0.91, 0.29, 0.37), 'Hilang': (0.96, 0.73, 0.24), 'Berlebih': (0.22, 0.60, 0.91)}.get(kind, (0.91, 0.29, 0.37))
                    sh = one[0].new_shape()
                    sh.draw_rect(rect)
                    sh.finish(color=rgb, fill=rgb, fill_opacity=.20, width=.9)
                    sh.commit()
                pix = one[0].get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                stream = io.BytesIO(pix.tobytes('png'))
                doc.add_picture(stream, width=usable)
            if pno < len(pdf) - 1:
                doc.add_page_break()
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
        # A valid Stage-2 review may have no discrepancy at all, yet still
        # contain checked location highlights that the user wants to export.
        has_annotations = bool(self._visible_stage2_marks('ref') or self._visible_stage2_marks('exam'))
        if not self.diffs and not has_annotations:
            QMessageBox.warning(self, 'Belum ada data', 'Belum ada temuan atau penanda Tahap 2 untuk diekspor.')
            return
        if self.waybill_mode:
            selected = self.choose_pdf_export_documents()
            if selected is None:
                return
            outputs = {
                'ref': ('Waybill_Rujukan_Beranotasi.pdf', lambda path: self.export_waybill_pdf(path, 'ref')),
                'exam': ('Waybill_Diperiksa_Beranotasi.pdf', lambda path: self.export_waybill_pdf(path, 'exam')),
                'corrected': ('Waybill_Hasil_Koreksi_Bersih.pdf', self.export_waybill_corrected_pdf),
                'notes': (correction_pdf_filename(self.exam_path),
                          lambda path: self.export_waybill_notes_pdf(
                              path, include_unchecked=(
                                  hasattr(self, 'workspace_pages') and
                                  self.workspace_pages.currentIndex() == 1 and
                                  self.correction_preview.all_notes.isChecked()))),
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
                    produced=[]; failures=[]
                    for key in selected:
                        filename, writer = outputs[key]
                        output_path = Path(td) / filename
                        try:
                            writer(output_path)
                            if output_path.is_file() and output_path.stat().st_size:
                                produced.append(output_path)
                            else:
                                failures.append(f'{filename}: PDF tidak dihasilkan')
                        except Exception as exc:
                            failures.append(f'{filename}: {exc}')
                    if not produced:
                        raise ValueError('Tidak ada PDF yang berhasil dibuat.\n' + '\n'.join(failures))
                    # Never write a PDF using a .zip file extension or vice versa.
                    if is_zip:
                        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for path in produced: zf.write(path, path.name)
                    else:
                        shutil.copyfile(produced[0], target)
                if failures:
                    QMessageBox.warning(self, 'Ekspor sebagian berhasil',
                        f'{len(produced)} PDF berhasil diekspor ke:\n{target}\n\nTidak berhasil:\n' + '\n'.join(failures))
                else:
                    QMessageBox.information(self, 'Selesai', f'{len(produced)} dokumen berhasil diekspor ke:\n{target}')
            except Exception as e:
                logging.exception('PDF export failed')
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
    def _log_event(self, action, detail=None):
        if getattr(self,'_restoring_session',False): return
        self.audit_events.append({'at':datetime.now(timezone.utc).isoformat(), 'action':action, 'detail':json.loads(json.dumps(detail or {},default=pdf_json_default))})
        if len(self.audit_events)>5000: self.audit_events=self.audit_events[-5000:]
        if hasattr(self,'autosave_timer') and self.ref_path and self.exam_path:
            self.autosave_timer.start()

    def _session_payload(self):
        if not self.ref_path or not self.exam_path or not self.ref_view.pdf or not self.exam_view.pdf:
            raise ValueError('Pilih dan bandingkan dua dokumen terlebih dahulu')
        baseline=self._snapshot_stage1()
        return {
            'documents':{'reference':fingerprint(self.ref_path),'examined':fingerprint(self.exam_path)},
            'comparison':{'waybill_mode':self.waybill_mode,'preset':self.rule_mode.currentData(),
                'reference_profile_selection':self.reference_profile_combo.currentData(),
                'reference_profile_detected':self._reference_profile_actual,
                'reference_field_map':self._reference_field_map,
                'fields':sorted(self.waybill_fields),'diffs':[asdict(x) for x in self.diffs],
                'baseline_diffs':[asdict(x) for x in baseline['diffs']],
                'ref_marks':self._marks_for_json(self.ref_marks),'exam_marks':self._marks_for_json(self.exam_marks),
                'baseline_ref_marks':self._marks_for_json(baseline['ref_marks']),
                'baseline_exam_marks':self._marks_for_json(baseline['exam_marks']),
                'ref_pages':self.ref_pages,'exam_pages':self.exam_pages,
                'baseline_ref_pages':baseline['ref_pages'],'baseline_exam_pages':baseline['exam_pages'],
                'reference':self.reference,'examined':self.examined,'reference_raw':self.reference_raw,
                'active_scope':sorted(getattr(self,'active_scope',set())),
                'uncertain':self.uncertain,'mode':self.mode,'rule_groups':self.rule_groups,
                'editor_text':self.editor_text,'note_overrides':self.note_overrides},
            'stage2':{'records':self.hybrid_stage2_records, 'annotations':self.stage2_annotations,
                'visibility':self.stage2_visibility},
            'viewer':{'ref_page':self.ref_view.page,'exam_page':self.exam_view.page,
                'ref_zoom':self.ref_view.zoom,'exam_zoom':self.exam_view.zoom},
            'audit':self.audit_events,
        }

    @staticmethod
    def _marks_for_json(marks):
        cleaned=[]
        for mark in marks:
            item=dict(mark)
            if 'rect' in item: item['rect']=list(fitz.Rect(item['rect']))
            cleaned.append(item)
        return cleaned

    def _autosave(self):
        if getattr(self,'_restoring_session',False):return
        try:
            target=self._session_file or (Path.home()/'Documents'/'DocMatch'/'autosave.dmjson')
            save_session(target,self._session_payload())
        except Exception:
            logging.exception('Autosave sesi gagal')

    def save_session_dialog(self):
        filename,_=QFileDialog.getSaveFileName(self,'Simpan Sesi DocMatch',
            str(Path.home()/'Documents'/'docmatch_sesi.dmjson'),'DocMatch Session (*.dmjson)')
        if not filename:return
        try:
            self.autosave_timer.stop()
            save_session(filename,self._session_payload())
            self._session_file=Path(filename)
            self.status.setText('Sesi tersimpan: '+filename)
        except Exception as exc:QMessageBox.critical(self,'Gagal menyimpan sesi',str(exc))

    def open_session_dialog(self):
        filename,_=QFileDialog.getOpenFileName(self,'Buka Sesi DocMatch',
            str(Path.home()/'Documents'),'DocMatch Session (*.dmjson)')
        if not filename:return
        try:
            payload=load_session(filename,check_files=True)
            self._restore_session(payload)
            self._session_file=Path(filename)
            QMessageBox.information(self,'Pemulihan sesi','Data, anotasi, dan hasil validasi berhasil dimuat. Periksa viewer dan ekspor sebelum melanjutkan.')
        except Exception as exc:QMessageBox.critical(self,'Pemulihan gagal',str(exc))

    def _restore_session(self, payload):
        data=payload['comparison']; stage2=payload['stage2']; view=payload.get('viewer',{})
        # Prepare and validate PDF previews before mutating the current workspace.
        ref=Path(payload['documents']['reference']['path']);exam=Path(payload['documents']['examined']['path'])
        a=self.work/'session_ref';b=self.work/'session_exam';a.mkdir(exist_ok=True);b.mkdir(exist_ok=True)
        refpdf=make_preview(ref,a); exampdf=make_preview(exam,b)
        with fitz.open(refpdf) as rd,fitz.open(exampdf) as ed:
            if not len(rd) or not len(ed):raise ValueError('PDF sesi kosong')
        self._restoring_session=True
        try:
            self.reset_comparison()
            self.ref_path=ref; self.exam_path=exam
            self.ref_btn.setText('Rujukan: '+ref.name);self.exam_btn.setText('Diperiksa: '+exam.name)
            preset=data['preset']; ix=self.rule_mode.findData(preset)
            if ix<0:raise ValueError('Mode parameter sesi tidak tersedia: '+str(preset))
            self.rule_mode.blockSignals(True)
            self.rule_mode.setCurrentIndex(ix)
            self.rule_mode.blockSignals(False)
            self.mode_changed()
            selection = data.get('reference_profile_selection', 'auto')
            ref_ix = self.reference_profile_combo.findData(selection)
            if ref_ix >= 0:
                self.reference_profile_combo.blockSignals(True)
                self.reference_profile_combo.setCurrentIndex(ref_ix)
                self.reference_profile_combo.blockSignals(False)
            self._reference_profile_actual = data.get('reference_profile_detected') or preset
            self._reference_field_map = dict(data.get('reference_field_map') or {})
            self.waybill_mode=bool(data['waybill_mode']);self.waybill_fields=set(data['fields'])
            cls=WaybillDifference if self.waybill_mode else Difference
            self.diffs=[cls(**d) for d in data['diffs']]
            self.ref_marks=self._marks_for_json(data['ref_marks']); self.exam_marks=self._marks_for_json(data['exam_marks'])
            self.ref_pages={int(k):v for k,v in data['ref_pages'].items()};self.exam_pages={int(k):v for k,v in data['exam_pages'].items()}
            self._stage1_baseline={
              'diffs':[cls(**d) for d in data['baseline_diffs']],
              'ref_marks':self._marks_for_json(data['baseline_ref_marks']),
              'exam_marks':self._marks_for_json(data['baseline_exam_marks']),
              'ref_pages':{int(k):v for k,v in data['baseline_ref_pages'].items()},
              'exam_pages':{int(k):v for k,v in data['baseline_exam_pages'].items()}}
            self.reference=data.get('reference',[]);self.examined=data.get('examined',[])
            self.reference_raw=data.get('reference_raw',[]);self.active_scope=set(data.get('active_scope',[]))
            self.uncertain=data.get('uncertain',[]);self.mode=data.get('mode','waybill')
            self.rule_groups=data.get('rule_groups',{})
            self.editor_text=data.get('editor_text');self.note_overrides=data.get('note_overrides',{})
            self.hybrid_stage2_records=copy.deepcopy(stage2['records'])
            self.stage2_annotations=copy.deepcopy(stage2['annotations'])
            self.stage2_visibility=copy.deepcopy(stage2['visibility'])
            self.audit_events=copy.deepcopy(payload.get('audit',[]))
            self.ref_view.load(refpdf,self.ref_marks);self.exam_view.load(exampdf,self.exam_marks)
            self.ref_view.set_zoom(view.get('ref_zoom',1.15));self.exam_view.set_zoom(view.get('exam_zoom',1.15))
            self.ref_view.goto(view.get('ref_page',0));self.exam_view.goto(view.get('exam_page',0))
            self.populate();self.enable_results();self._refresh_export_annotations();self._refresh_main_annotation_previews();self.show_step(1)
            self.status.setText(f'Sesi dipulihkan • {len(self.diffs)} temuan • {len(self.hybrid_stage2_records)} validasi Tahap 2')
        finally:
            self._restoring_session=False

    def open_template_manager(self):
        """Edit alias metadata in an offline JSON file; extraction rules remain untouched."""
        target=Path.home()/'Documents'/'DocMatch'/'template_aliases.json'
        try: current=read_templates(target)
        except Exception as exc:
            QMessageBox.critical(self,'Template tidak valid',str(exc));return
        text,ok=QInputDialog.getMultiLineText(self,'Template Manager — Alias Parameter',
            'Alias per parameter dalam JSON. Belum memodifikasi koordinat/mesin ekstraksi:',
            json.dumps(current,ensure_ascii=False,indent=2))
        if not ok:return
        try:
            write_templates(target,json.loads(text))
            QMessageBox.information(self,'Template disimpan',
                'Alias template tersimpan lokal. Ini metadata persiapan; belum diterapkan pada mesin ekstraksi.')
        except Exception as exc:QMessageBox.critical(self,'Gagal menyimpan template',str(exc))

    def closeEvent(self, event):
        if self.ref_path and self.exam_path and (self.diffs or self.hybrid_stage2_records):
            self.autosave_timer.stop(); self._autosave()
        super().closeEvent(event)

    def export_report(self):
        if not self.diffs and not self.hybrid_stage2_records:
            QMessageBox.warning(self,'Belum ada laporan','Jalankan perbandingan dan/atau validasi tahap kedua.');return
        name,_=QFileDialog.getSaveFileName(self,'Simpan laporan','docmatch_laporan.json','JSON (*.json)')
        if name:
            report={'reference':str(self.ref_path),'examined':str(self.exam_path),'scope':{'mode':self.mode,'waybill_preset':self.rule_mode.currentData() if self.waybill_mode else None,'reference_profile':getattr(self,'_reference_profile_actual',None) if self.waybill_mode else None,'reference_field_map':getattr(self,'_reference_field_map',{}) if self.waybill_mode else {},'waybill_fields':sorted(self.waybill_fields) if self.waybill_mode else [],'selected_reference_blocks':[i+1 for i in sorted(self.active_scope)],'unchecked_reference_blocks':[i+1 for i in range(len(self.reference)) if i not in self.active_scope],'unmapped_reference_blocks':[i+1 for i in self.uncertain],'embedded_groups':self.rule_groups},'audit_history':self.audit_events,'manual_editor':{'used':self.editor_text is not None,'edited_text':self.editor_text if self.editor_text is not None else None},'limitations':'Waybill: ekspor PDF merupakan salinan audit beranotasi, bukan koreksi otomatis; DOCX berisi tabel temuan editable dan gambar halaman. Ekstraksi berbasis template ANL belum universal. Mode umum membangun ulang teks.','hybrid_stage2':{'annotations':self.stage2_annotations,'visible_fields':[f for f in self.stage2_annotations if self.stage2_visibility.get(f,True)],'records':list(self.hybrid_stage2_records.values()),'stage1_baseline_preserved_for_audit':True,'active_findings_updated':self.waybill_mode,'original_differences':[asdict(d) for d in (self._stage1_baseline or {}).get('diffs',[])]},'differences':[
                {**asdict(d),'number':i+1,'reference_page':self.ref_pages.get(i+1, -1)+1 if i+1 in self.ref_pages else None,
                 'examined_page':self.exam_pages.get(i+1,-1)+1 if i+1 in self.exam_pages else None} for i,d in enumerate(self.diffs)]}
            Path(name).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=pdf_json_default),encoding='utf-8')
            QMessageBox.information(self,'Selesai','Laporan disimpan.')

if __name__=='__main__':
    set_windows_app_id()
    logging.basicConfig(filename=str(Path.home()/'docmatch_errors.log'), level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')
    app=QApplication(sys.argv)
    app.setApplicationName('DocMatch')
    app.setOrganizationName('DocMatch')
    app.setWindowIcon(app_icon())
    splash = None
    logo_file = asset_path('docmatch_logo.png')
    if logo_file.is_file():
        splash_pixmap = QPixmap(str(logo_file))
        if not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            splash.show()
            app.processEvents()
    w=Window()
    w.show()
    if splash is not None:
        splash.finish(w)
    sys.exit(app.exec())
