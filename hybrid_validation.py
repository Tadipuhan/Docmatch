"""DocMatch second-stage verification, with controlled promotion into stage-one findings."""
from __future__ import annotations
import difflib
import threading
import re
from region_ocr_recovery import text_quality, read_region_candidates
from gsl_ocr import OCRError
from textnorm import normalize_text
from region_guard import check_ocr_relevance
from datetime import datetime, timezone
from pathlib import Path

import pymupdf as fitz
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize, QObject, QRunnable, QThreadPool, QTimer
from PySide6.QtGui import QColor, QBrush, QPen, QPainter, QPixmap, QImage, QFont
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QSplitter, QPlainTextEdit, QMessageBox, QFileDialog, QListWidget,
    QAbstractItemView, QFrame, QProgressBar, QFormLayout, QLineEdit, QGroupBox,
    QSizePolicy, QToolButton, QScrollBar, QSplitterHandle, QInputDialog,
    QMenu, QWidgetAction, QListWidgetItem, QCheckBox,
)


def _normalize(text):
    return re.sub(r'[^\w]+', '', text or '').casefold()


def _tokenize(text):
    return set(re.findall(r'[\w]+', (text or '').casefold()))


def _rect_json(rect):
    return [round(float(v), 3) for v in tuple(rect)]


def _native_by_field(doc, page_no):
    """Teks Type3 terdekode per kotak GSL halaman ini (untuk validasi relevansi OCR)."""
    try:
        from gsl_layout import boxes_for_page
        from gsl_font_recovery import recover_page_words, word_anchor
        if page_no != 0:
            return {}
        page = doc[page_no]
        words = recover_page_words(doc, page_no)
        boxes, _ = boxes_for_page(page)
    except Exception:
        return {}
    r = page.rect
    out = {}
    for name, (x0, y0, x1, y1) in boxes.items():
        cell = fitz.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height,
                         r.x0 + x1 * r.width, r.y0 + y1 * r.height)
        out[name] = ' '.join(w['word'] for w in words if cell.contains(word_anchor(w)))
    return out


def _ocr_rect(page, region, field, profile):
    """Kotak OCR otomatis: lewati caption cetak di bagian atas kotak GSL."""
    if profile != 'waybill_gsl':
        return region
    if getattr(page.parent, 'name', None):
        from flexible_reference import detect_flexible_pdf
        if detect_flexible_pdf(page.parent.name):
            return region
    try:
        from gsl_layout import GSL_BOXES, inset_for_ocr
        if field not in GSL_BOXES or page.number != 0:
            return region
        r = page.rect
        x0, y0, x1, y1 = inset_for_ocr(field, GSL_BOXES[field])
        inner = fitz.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height,
                          r.x0 + x1 * r.width, r.y0 + y1 * r.height) & fitz.Rect(region)
        return inner if inner.width > 4 and inner.height > 3 else region
    except Exception:
        return region


def extract_region(page, rect, profile=''):
    """Return extractable text and token boxes; don't invent content for scans."""
    clip = fitz.Rect(rect) & page.rect
    if clip.is_empty or clip.width < 2 or clip.height < 2:
        return {'text': '', 'boxes': [], 'source': 'empty', 'readable': False}
    words = []
    # The selected GSL profile describes the comparison schema, not necessarily
    # the font/layout of this specific PDF. Reference letters use native text.
    flexible = False
    if profile == 'waybill_gsl' and getattr(page.parent,'name',None):
        from flexible_reference import detect_flexible_pdf
        flexible = detect_flexible_pdf(page.parent.name)
    if profile == 'waybill_gsl' and not flexible:
        from gsl_font_recovery import recover_page_words
        try:
            words = [
                {'text': str(w['word']), 'rect': fitz.Rect(w['rect'])}
                for w in recover_page_words(page.parent, page.number)
                if clip.intersects(fitz.Rect(w['rect']))
                and clip.contains((fitz.Rect(w['rect']).tl + fitz.Rect(w['rect']).br) * 0.5)
            ]
        except (ValueError, RuntimeError, KeyError, TypeError):
            words = []
    else:
        words = [
            {'text': str(w[4]), 'rect': fitz.Rect(w[:4])}
            for w in page.get_text('words', clip=clip, sort=True)
            if str(w[4]).strip()
        ]
        if profile in ('waybill', 'waybill_anl'):
            # v1.8.33.2: kata dimiliki kotak bila titik tengahnya di dalam kotak (bukan sekadar
            # bersinggungan), agar kata field tetangga tidak ikut terbaca.
            words = [w for w in words if clip.contains((w['rect'].tl + w['rect'].br) * 0.5)]
    text = ' '.join(w['text'] for w in words)
    readable = not text_quality(text)['suspicious']
    return {'text': text, 'boxes': [_rect_json(w['rect']) for w in words],
            'source': 'Type3' if profile == 'waybill_gsl' and not flexible else 'PDF text layer',
            'readable': readable, 'quality': text_quality(text)}


def refined_highlight_rect(region, extraction, padding=1.6):
    """Visual-only glyph/word union; OCR continues to use the full selected region.

    Reject suspicious/partial boxes so invalid Type3 geometry never clips text.
    """
    region = fitz.Rect(region)
    boxes = []
    for raw in extraction.get('boxes', []):
        box = fitz.Rect(raw)
        if box.is_empty or box.width < 0.4 or box.height < 0.4:
            continue
        box = box & region
        if box.is_empty or box.get_area() < 0.1:
            continue
        boxes.append(box)
    if not boxes or not extraction.get('readable'):
        return region
    union = fitz.Rect(boxes[0])
    for box in boxes[1:]:
        union |= box
    union = fitz.Rect(union.x0-padding, union.y0-padding,
                      union.x1+padding, union.y1+padding) & region
    ratio = union.get_area() / max(region.get_area(), 1)
    return union if 0.015 <= ratio <= 0.96 else region


def preset_candidates(doc, field, profile):
    if not str(profile).startswith('waybill'):
        return []
    from waybill_rules import _profile_cells
    cells = _profile_cells(profile, doc if profile == 'waybill_msc' else (doc[0] if profile in ('waybill_maersk','waybill_meratus') and len(doc) else None))
    regions = cells.get(field, [])
    out = []
    for no, x0, y0, x1, y1 in regions:
        if field.startswith('Attached List -') and profile == 'waybill_gsl':
            no = len(doc) - 1
        if 0 <= no < len(doc):
            bounds = doc[no].rect
            out.append((no, fitz.Rect(bounds.x0 + x0*bounds.width,
                                      bounds.y0 + y0*bounds.height,
                                      bounds.x0 + x1*bounds.width,
                                      bounds.y0 + y1*bounds.height)))
    return out


def find_candidates(doc, field, text, profile):
    """Conservative candidate retrieval: field layout + text search, not copied coordinates."""
    if profile == 'waybill_gsl' and getattr(doc, 'name', None):
        from flexible_reference import detect_flexible_pdf, extract_flexible
        if detect_flexible_pdf(doc.name):
            info = extract_flexible(doc.name, [field])[field]
            if info.get('valid') and info['words']:
                page_no = info['words'][0]['page']
                boxes = [fitz.Rect(w['rect']) for w in info['words'] if w['page'] == page_no]
                union = fitz.Rect(boxes[0])
                for box in boxes[1:]: union |= box
                area = (union + (-2,-2,2,2)) & doc[page_no].rect
                value = extract_region(doc[page_no], area, profile)
                # This is label-based; do not run original GSL template locators.
                return [{'page':page_no,'rect':area,'reason':'field label (flexible reference)',
                         'score':.95,'extraction':value}]
            return []
    results = []
    for page_no, rect in preset_candidates(doc, field, profile):
        value = extract_region(doc[page_no], rect, profile)
        if value['readable']:
            results.append({'page': page_no, 'rect': rect, 'reason': 'template field',
                            'score': .82, 'extraction': value})
        else:
            # Unknown scan/Type3: region location may be valid but text is not.
            results.append({'page': page_no, 'rect': rect, 'reason': 'template region; text unverified',
                            'score': .48, 'extraction': value})
    if text.strip() and profile != 'waybill_gsl':
        fragments = [text.strip()[:80]]
        fragments += [x for x in re.findall(r'[\w.-]{4,}', text)[:5] if x not in fragments]
        for page_no, page in enumerate(doc):
            for term in fragments:
                for match in page.search_for(term)[:12]:
                    expand = fitz.Rect(match.x0-4, match.y0-3, match.x1+4, match.y1+3) & page.rect
                    value = extract_region(page, expand, profile)
                    sim = difflib.SequenceMatcher(None, _normalize(text), _normalize(value['text'])).ratio()
                    results.append({'page': page_no, 'rect': expand, 'reason': 'similar text',
                                    'score': min(.75, .35 + .4*sim), 'extraction': value})
    results.sort(key=lambda v: v['score'], reverse=True)
    unique=[]
    for candidate in results:
        if any(candidate['page']==r['page'] and
               (candidate['rect'] & r['rect']).get_area() > .7*min(candidate['rect'].get_area(),r['rect'].get_area())
               for r in unique):
            continue
        unique.append(candidate)
        if len(unique)>=12:break
    return unique


class AutoLocateSignals(QObject):
    finished = Signal(int, str, object)


class AutoLocateTask(QRunnable):
    """Use independent fitz documents in a background thread. Never touch Qt widgets."""
    def __init__(self, generation, field, path_a, path_b, profile, stage1):
        super().__init__()
        self.generation, self.field = generation, field
        self.path_a, self.path_b = path_a, path_b
        self.profile, self.stage1 = profile, dict(stage1 or {})
        self.signals = AutoLocateSignals()

    def compute(self):
        payload = {'sides': {}, 'errors': []}
        for side, path, target in (
                ('A', self.path_a, self.stage1.get('reference_text', '')),
                ('B', self.path_b, self.stage1.get('examined_text', ''))):
            try:
                with fitz.open(path) as doc:
                    found = find_candidates(doc, self.field, str(target or ''), self.profile)
                    if not found:
                        payload['sides'][side] = {'found': False, 'reason': 'Tidak ada kandidat'}
                        continue
                    best = found[0]
                    region = best['rect']
                    native = best['extraction']
                    data = {'found': True, 'page': best['page'],
                            'rect': _rect_json(region), 'reason': best['reason'],
                            'score': best['score'], 'native': native, 'ocr': [],
                            'alternatives': [dict(page=c['page'], rect=_rect_json(c['rect']),
                                                  reason=c['reason'], score=c['score'])
                                             for c in found[:6]]}
                    # Two-pass OCR: pass 1 for ordinary text; pass 2 automatically
                    # when empty, corrupt or clearly uncertain. Both PDFs are processed.
                    # Never promote OCR output without a user's confirmation.
                    try:
                        ocr_box = _ocr_rect(doc[best['page']], region, self.field, self.profile)
                        data['ocr'] = read_region_candidates(doc[best['page']], ocr_box,
                                                           modes=(6,), variants=('grayscale',))
                        first = data['ocr'][0] if data['ocr'] else None
                        fallback = (not first or not first.get('text', '').strip()
                                    or text_quality(first['text'])['suspicious']
                                    or first.get('confidence', 0) < 78
                                    or text_quality(native.get('text', ''))['suspicious'])
                        if fallback:
                            data['ocr_fallback_used'] = True
                            more = read_region_candidates(doc[best['page']], ocr_box,
                                                          modes=(11, 7), variants=('grayscale', 'warna'))
                            unique = {c['text']: c for c in data['ocr'] if c.get('text', '').strip()}
                            for candidate in more:
                                t = candidate.get('text', '').strip()
                                if t and (t not in unique or candidate['confidence'] > unique[t]['confidence']):
                                    unique[t] = candidate
                            data['ocr'] = sorted(unique.values(),
                                key=lambda c: (c['confidence'], c['words']), reverse=True)[:6]
                        else:
                            data['ocr_fallback_used'] = False
                    except (OCRError, OSError, ValueError, RuntimeError) as exc:
                        data['ocr_error'] = str(exc)
                    if data.get('ocr') and self.profile == 'waybill_gsl':
                        # v1.8.30.9: tolak OCR yang ternyata berasal dari field lain.
                        native_all = _native_by_field(doc, best['page'])
                        kept, rejected = [], []
                        for cand in data['ocr']:
                            ok, why = check_ocr_relevance(self.field, cand.get('text', ''), native_all)
                            (kept if ok else rejected).append(cand if ok else dict(cand, reject_reason=why))
                        data['ocr'], data['ocr_rejected'] = kept, rejected
                    payload['sides'][side] = data
            except (OSError, RuntimeError, ValueError, KeyError) as exc:
                payload['sides'][side] = {'found': False, 'reason': str(exc)}
                payload['errors'].append(f'{side}: {exc}')
        return payload

    def run(self):
        self.signals.finished.emit(self.generation, self.field, self.compute())


class BatchSignals(QObject):
    field_ready = Signal(str, object, int, int)
    complete = Signal(int)


class BatchPageOneTask(QRunnable):
    """Precompute selected page-one fields sequentially without mutating UI/stage one."""
    def __init__(self, fields, reference, examined, profile, stage1):
        super().__init__()
        self.fields = list(fields)
        self.reference, self.examined, self.profile = reference, examined, profile
        self.stage1 = stage1
        self.signals = BatchSignals()
        self.cancelled = threading.Event()

    def run(self):
        for position, field in enumerate(self.fields, 1):
            if self.cancelled.is_set():
                break
            task = AutoLocateTask(0, field, self.reference, self.examined,
                                  self.profile, self.stage1.get(field, {}))
            try:
                payload = task.compute()
            except Exception as exc:
                payload = {'sides': {}, 'errors': [str(exc)]}
            self.signals.field_ready.emit(field, payload, position, len(self.fields))
        if not self.cancelled.is_set():
            self.signals.complete.emit(len(self.fields))


class RegionCanvas(QWidget):
    selected = Signal(object)
    preview_changed = Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None
        self.page_index = 0
        self.zoom = 1.15
        self.region = None
        self.overlays = {}  # field -> {'page': int, 'rect': fitz.Rect}; checked only
        self.candidate = False
        self.pixmap = QPixmap()
        self.mode = 'draw'
        self._anchor = None
        self._initial = None
        self._drag = None
        self.setMouseTracking(True)
        self.setMinimumSize(250, 330)

    def display(self, doc, page=0):
        self.doc = doc
        self.page_index = max(0, min(page, len(doc)-1))
        # HiDPI raster: 2 source pixels per Qt logical pixel, keeping selection mapping in PDF coordinates.
        ratio = 2.0
        pix = doc[self.page_index].get_pixmap(matrix=fitz.Matrix(self.zoom*ratio,self.zoom*ratio), alpha=False)
        self.pixmap = QPixmap.fromImage(QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy())
        self.pixmap.setDevicePixelRatio(ratio)
        size = QSize(round(pix.width/ratio), round(pix.height/ratio))
        self.resize(size)
        self.setMinimumSize(size)
        self.update()

    def page_rect(self):
        return self.doc[self.page_index].rect

    def _screen_to_pdf(self, point):
        page = self.page_rect()
        return QPointF(page.x0 + point.x()/self.zoom, page.y0 + point.y()/self.zoom)

    def _pdf_to_screen(self, rect):
        page = self.page_rect()
        return QRectF((rect.x0-page.x0)*self.zoom,(rect.y0-page.y0)*self.zoom,
                      rect.width*self.zoom,rect.height*self.zoom)

    def set_region(self, page_no, rect, candidate=False):
        self.region = fitz.Rect(rect)
        self.candidate = candidate
        if page_no != self.page_index:
            self.display(self.doc,page_no)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pixmap.isNull():
            painter.drawPixmap(0,0,self.pixmap)
        # Persistent, field-keyed highlights; unrelated checked boxes remain visible.
        for field, info in self.overlays.items():
            if info['page'] != self.page_index:
                continue
            rect = fitz.Rect(info['rect'])
            if rect.is_empty or rect.is_infinite:
                continue
            box = self._pdf_to_screen(rect)
            is_active = bool(self.property('active_field') == field)
            color = QColor('#B91C1C' if is_active else '#2678AD')
            fill = QColor(color); fill.setAlpha(22 if not is_active else 35)
            painter.fillRect(box, fill)
            painter.setPen(QPen(color, 1.5 if is_active else 1.1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(box)
        # The active outline must obey the same checkbox as stored overlays.
        if self.region and self.property('active_field') and self.property('active_field') in self.overlays:
            box = self._pdf_to_screen(self.region)
            color = QColor('#C18412' if self.candidate else '#AD1429')
            fill = QColor(color); fill.setAlpha(35)
            painter.fillRect(box, fill)
            painter.setPen(QPen(color,2,Qt.PenStyle.DashLine if self.candidate else Qt.PenStyle.SolidLine))
            painter.drawRect(box)
            painter.setPen(QPen(color,1))
            painter.setBrush(QBrush(QColor('white')))
            for x in (box.left(),box.center().x(),box.right()):
                for y in (box.top(),box.center().y(),box.bottom()):
                    painter.drawRect(QRectF(x-3.5,y-3.5,7,7))
        painter.end()

    def _handle(self, pos):
        if self.region is None:return None
        box = self._pdf_to_screen(self.region)
        if not box.adjusted(-7,-7,7,7).contains(pos):return None
        xs=[('l',box.left()),('c',box.center().x()),('r',box.right())]
        ys=[('t',box.top()),('c',box.center().y()),('b',box.bottom())]
        for xname,x in xs:
            for yname,y in ys:
                if abs(pos.x()-x)<8 and abs(pos.y()-y)<8 and (xname,yname)!=('c','c'):
                    return xname+yname
        if box.contains(pos):return 'move'
        return None

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton or self.doc is None:return
        self._anchor = self._screen_to_pdf(event.position())
        self._initial = fitz.Rect(self.region) if self.region else None
        self._drag = self._handle(event.position()) or 'draw'
        if self._drag == 'draw':
            self.region = fitz.Rect(self._anchor.x(),self._anchor.y(),self._anchor.x(),self._anchor.y())
        self.update()

    def mouseMoveEvent(self,event):
        if self._drag is None or self._anchor is None:return
        at=self._screen_to_pdf(event.position())
        if self._drag == 'draw':
            self.region=fitz.Rect(min(at.x(),self._anchor.x()),min(at.y(),self._anchor.y()),
                                  max(at.x(),self._anchor.x()),max(at.y(),self._anchor.y()))
        elif self._initial is not None:
            start=self._initial
            dx=at.x()-self._anchor.x();dy=at.y()-self._anchor.y()
            if self._drag=='move':
                candidate=start+fitz.Rect(dx,dy,dx,dy)
            else:
                candidate=fitz.Rect(start)
                if 'l' in self._drag:candidate.x0+=dx
                if 'r' in self._drag:candidate.x1+=dx
                if 't' in self._drag:candidate.y0+=dy
                if 'b' in self._drag:candidate.y1+=dy
                candidate=fitz.Rect(min(candidate.x0,candidate.x1),min(candidate.y0,candidate.y1),
                                    max(candidate.x0,candidate.x1),max(candidate.y0,candidate.y1))
            self.region=candidate
        self.candidate=False
        self.update()
        if self.region and self.region.width >= 2 and self.region.height >= 2:
            self.preview_changed.emit({'page': self.page_index, 'rect': fitz.Rect(self.region)})

    def mouseReleaseEvent(self,event):
        if self._drag is None:return
        self._drag=None
        if self.region:
            self.region=self.region & self.page_rect()
            if self.region.width>=2 and self.region.height>=2:
                self.selected.emit({'page':self.page_index,'rect':fitz.Rect(self.region)})
            else:
                self.region=None
        self.update()


class RegionViewer(QWidget):
    selected = Signal(object)
    preview_changed = Signal(object)
    def __init__(self, doc, title):
        super().__init__();self.doc=doc
        layout=QVBoxLayout(self)
        line=QHBoxLayout();line.addWidget(QLabel(title));line.addStretch()
        self.prev=QPushButton('‹');self.next=QPushButton('›');self.counter=QLabel()
        self.minus=QPushButton('−');self.plus=QPushButton('+');self.fit=QPushButton('Lebar')
        for x in (self.prev,self.counter,self.next,self.minus,self.plus,self.fit):line.addWidget(x)
        layout.addLayout(line)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(False)
        self.canvas=RegionCanvas();self.scroll.setWidget(self.canvas);layout.addWidget(self.scroll,1)
        self.canvas.selected.connect(self.selected)
        self.canvas.preview_changed.connect(self.preview_changed)
        self.prev.clicked.connect(lambda:self.goto(self.canvas.page_index-1))
        self.next.clicked.connect(lambda:self.goto(self.canvas.page_index+1))
        self.minus.clicked.connect(lambda:self.set_zoom(self.canvas.zoom-.15))
        self.plus.clicked.connect(lambda:self.set_zoom(self.canvas.zoom+.15))
        self.fit.clicked.connect(self.fit_width)
        self.goto(0)

    def goto(self, page):
        if 0 <= page < len(self.doc):
            self.canvas.display(self.doc,page)
            self.counter.setText(f'{page+1}/{len(self.doc)}')

    def set_zoom(self,zoom):
        self.canvas.zoom=max(.6,min(2.5,zoom))
        self.goto(self.canvas.page_index)

    def fit_width(self):
        if len(self.doc):
            available = max(180, self.scroll.viewport().width()-12)
            self.set_zoom(available / max(1, self.doc[self.canvas.page_index].rect.width))

    def show_region(self,page,rect,candidate=False):
        self.goto(page)
        self.canvas.set_region(page,rect,candidate)
        self.scroll.ensureVisible(int((rect.x0+rect.x1)/2*self.canvas.zoom),
                                  int((rect.y0+rect.y1)/2*self.canvas.zoom),80,80)


class HybridValidationDialog(QDialog):
    """Stage 2: parameter checklist + dual PDF canvas + crop/validation inspector.

    Stage-one data remain untouched. The view uses original RegionViewer/RegionCanvas;
    only the workspace and selection-review workflow are reorganised here.
    """
    def __init__(self, reference_pdf, examined_pdf, fields, profile='', parent=None, stage1_fields=None):
        super().__init__(parent)
        self.setWindowTitle('DocMatch — Verifikasi Hasil (Tahap 2) | v1.8.28')
        self.resize(1580, 920)
        self.setMinimumSize(850, 580)
        self.reference_path = str(reference_pdf)
        self.examined_path = str(examined_pdf)
        self.ref_doc = fitz.open(self.reference_path)
        self.exam_doc = fitz.open(self.examined_path)
        self.profile = profile
        self.records = {}
        self.stage1_fields = stage1_fields or {}
        self._sidebar_sizes = [1060, 420]
        self.candidates = []
        self.selection = {'A': None, 'B': None}
        self._confirmed = {'A': False, 'B': False}
        self._source_kind = {'A': '', 'B': ''}
        self._dirty = False
        self._ocr_choice = {'A': None, 'B': None}
        self._auto_pool = QThreadPool(self)
        self._auto_pool.setMaxThreadCount(1)  # i5 / 8GB: avoid concurrent OCR workloads.
        self._auto_generation = 0
        self._auto_cache = {}
        self._auto_workers = {}  # keep signal owners alive until finished
        self._auto_loading = False
        self._auto_review_required = False
        self._recover_requested = False
        self.annotation_regions = {}  # All page-one selections, independent from active field
        self.annotation_visibility = {name: True for name in set(fields)}
        self._batch_results = {}
        self._batch_done = 0
        self._batch_total = 0
        self._batch_task = None
        self._field_names = sorted(set(fields), key=lambda x: x.casefold())
        self._build_ui()
        self._connect_events()
        self._refresh_checklist()
        if self.field_list.count():
            self.field_list.setCurrentRow(0)
        # Start preflight after dialog becomes visible. No Stage-1 mutations.
        QTimer.singleShot(0, self._start_page_one_batch)

    def _section_title(self, text):
        label = QLabel(text)
        label.setStyleSheet('font-weight: 700; font-size: 12px; color: #9B2335;')
        return label

    def _collapsible(self, title, content, expanded=True):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        toggle = QToolButton()
        toggle.setText(title)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        toggle.setCheckable(True)
        toggle.setChecked(expanded)
        toggle.setStyleSheet('QToolButton { text-align: left; font-weight: 700; color: #991B2B; background:#F2F3F5; border:0; padding:9px; }')
        layout.addWidget(toggle)
        layout.addWidget(content)
        content.setVisible(expanded)
        def changed(opened):
            content.setVisible(opened)
            toggle.setArrowType(Qt.ArrowType.DownArrow if opened else Qt.ArrowType.RightArrow)
        toggle.toggled.connect(changed)
        return wrapper

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self._sidebar_sizes = self.main_split.sizes()
            self.sidebar.hide()
            self.sidebar_toggle.setText('◀  Tampilkan Panel Kanan')
            self.status.setText('Panel kanan disembunyikan. Klik Tampilkan Panel Kanan untuk membuka daftar parameter dan inspector.')
        else:
            self.sidebar.show()
            self.main_split.setSizes(self._sidebar_sizes)
            self.sidebar_toggle.setText('▶  Sembunyikan Panel Kanan')

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background: #F3F4F6; color: #20242B; }
            QFrame#surface { background: #FFFFFF; border: 1px solid #DCE0E5; border-radius: 8px; }
            QPushButton { padding: 7px 10px; border: 1px solid #CDD2D8; border-radius: 5px; background: #FFFFFF; }
            QPushButton:hover { background: #F6E7EB; border-color: #B94A59; }
            QPushButton#primary { background: #991B2B; border: 1px solid #991B2B; color: white; font-weight: 700; }
            QPushButton#primary:hover { background: #7F1422; }
            QListWidget { border: 1px solid #DFE2E7; border-radius: 5px; background: white; outline: 0; }
            QListWidget::item { padding: 7px 6px; border-bottom: 1px solid #F0F1F2; }
            QListWidget::item:selected { background: #F9E7EA; color: #811423; border-left: 3px solid #991B2B; }
            QPlainTextEdit { border: 1px solid #D5DAE0; border-radius: 5px; background: white; padding: 5px; }
            QProgressBar { border: 1px solid #DCE0E5; border-radius: 4px; background: #F0F0F0; text-align: center; height: 16px; }
            QProgressBar::chunk { background: #991B2B; border-radius: 3px; }
            QSplitter::handle { background: #E3E5E8; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(8)
        header = QHBoxLayout()
        titlebox = QVBoxLayout()
        title = QLabel('VERIFIKASI HASIL  /  TAHAP 2')
        title.setStyleSheet('font-size: 16px; font-weight: 800; color: #7F1422;')
        titlebox.addWidget(title)
        subtitle = QLabel('Tanpa perubahan: Berikutnya. Ada koreksi: seleksi, konfirmasi, dan perbarui hasil Tahap 1.')
        subtitle.setStyleSheet('color: #586272; font-size: 11px;')
        titlebox.addWidget(subtitle)
        header.addLayout(titlebox, 1)
        self.sidebar_toggle = QPushButton('▶  Sembunyikan Panel Kanan')
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        header.addWidget(self.sidebar_toggle)
        self.save = QPushButton('Ekspor JSON')
        header.addWidget(self.save)
        root.addLayout(header)
        self.main_split = QSplitter(Qt.Orientation.Horizontal)
        self.main_split.setChildrenCollapsible(False)
        root.addWidget(self.main_split, 1)

        center = QFrame();center.setObjectName('surface');center.setMinimumWidth(450)
        center_l = QVBoxLayout(center);center_l.setContentsMargins(8, 10, 8, 8);center_l.setSpacing(8)
        row = QHBoxLayout();row.addWidget(self._section_title('DOKUMEN A & B'));row.addStretch()
        self.zoom_hint = QLabel('Drag / geser / resize · sinkron dua arah · HiDPI')
        self.zoom_hint.setStyleSheet('color: #687180; font-size: 10px;')
        row.addWidget(self.zoom_hint);center_l.addLayout(row)
        self.docs_split = QSplitter(Qt.Orientation.Horizontal)
        self.docs_split.setChildrenCollapsible(False)
        self.a = RegionViewer(self.ref_doc, 'PDF A — RUJUKAN')
        self.b = RegionViewer(self.exam_doc, 'PDF B — DIPERIKSA')
        self.a.setMinimumWidth(220);self.b.setMinimumWidth(220)
        self.docs_split.addWidget(self.a);self.docs_split.addWidget(self.b)
        self.docs_split.setStretchFactor(0, 1);self.docs_split.setStretchFactor(1, 1)
        center_l.addWidget(self.docs_split, 1)
        syncrow = QHBoxLayout()
        self.sync_coordinates = QCheckBox('Koordinat sinkron A ⇄ B (posisi relatif sama)')
        self.sync_coordinates.setChecked(True)
        self.sync_coordinates.setToolTip('Saat seleksi, geser atau resize satu kotak, kotak lain mengikuti persentase posisi pada halaman yang sama. Nonaktifkan bila layout A/B berbeda.')
        syncrow.addWidget(self.sync_coordinates)
        syncrow.addStretch(1)
        center_l.addLayout(syncrow)
        self.main_split.addWidget(center)

        self.sidebar = QFrame();self.sidebar.setObjectName('surface');self.sidebar.setMinimumWidth(280)
        sidebar_l = QVBoxLayout(self.sidebar)
        sidebar_l.setContentsMargins(7, 7, 7, 7);sidebar_l.setSpacing(4)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_root = QWidget()
        right_l = QVBoxLayout(sidebar_root)
        right_l.setContentsMargins(2, 2, 2, 2)
        right_l.setSpacing(7)

        checklist = QWidget()
        checklist_l = QVBoxLayout(checklist)
        checklist_l.setContentsMargins(5, 3, 5, 5)
        self.batch_status = QLabel('Analisis halaman 1: belum dijalankan')
        self.batch_status.setWordWrap(True)
        self.batch_status.setStyleSheet('color: #596575; font-size: 10px;')
        checklist_l.addWidget(self.batch_status)
        self.batch_progress = QProgressBar()
        self.batch_progress.setValue(0)
        checklist_l.addWidget(self.batch_progress)
        self.progress_text = QLabel('0 / 0 dikonfirmasi')
        self.progress_text.setStyleSheet('color: #586272; font-size: 11px;')
        checklist_l.addWidget(self.progress_text)
        self.progress = QProgressBar(); self.progress.setTextVisible(False)
        checklist_l.addWidget(self.progress)
        self.field_list = QListWidget()
        self.field_list.setMinimumHeight(160)
        self.field_list.setMaximumHeight(280)
        self.field_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for field_name in self._field_names:
            entry = QListWidgetItem(field_name)
            entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            entry.setCheckState(Qt.CheckState.Checked)
            self.field_list.addItem(entry)
        self.parameter_search = QLineEdit()
        self.parameter_search.setPlaceholderText('Cari parameter…')
        checklist_l.addWidget(self.parameter_search)
        checklist_l.addWidget(self.field_list)
        self.prev_field = QPushButton('‹ Sebelumnya')
        self.next_field = QPushButton('Berikutnya ›')
        nav = QHBoxLayout();nav.addWidget(self.prev_field);nav.addWidget(self.next_field)
        checklist_l.addLayout(nav)
        right_l.addWidget(self._collapsible('DAFTAR PARAMETER', checklist, True))

        inspector = QWidget()
        inspector_l = QVBoxLayout(inspector)
        inspector_l.setContentsMargins(5, 4, 5, 5)
        inspector_l.setSpacing(7)
        # Inspector is independently collapsible and scrolls with the right sidebar.
        right_l_original = right_l
        right_l = inspector_l
        self.active_field = QLabel('—')
        self.active_field.setWordWrap(True)
        self.active_field.setStyleSheet('font-size: 13px; font-weight: 700;')
        right_l.addWidget(self.active_field)
        self.result_tag = QLabel('BELUM DIPERIKSA')
        self.result_tag.setStyleSheet('background: #EEF0F3; color: #485363; border-radius: 4px; padding: 5px; font-weight: 700;')
        right_l.addWidget(self.result_tag)
        right_l.addWidget(QLabel('CROP AREA A  ·  RUJUKAN'))
        self.crop_a = QLabel('Pilih kotak pada PDF A')
        self._setup_crop(self.crop_a)
        right_l.addWidget(self.crop_a)
        right_l.addWidget(QLabel('CROP AREA B  ·  DIPERIKSA'))
        self.crop_b = QLabel('Belum ada kandidat')
        self._setup_crop(self.crop_b)
        right_l.addWidget(self.crop_b)
        magnify = QHBoxLayout()
        self.zoom_crop_a = QPushButton('Perbesar Crop A')
        self.zoom_crop_b = QPushButton('Perbesar Crop B')
        magnify.addWidget(self.zoom_crop_a);magnify.addWidget(self.zoom_crop_b)
        right_l.addLayout(magnify)
        right_l.addWidget(QLabel('TEKS A  ·  dapat dikoreksi'))
        self.a_text = QPlainTextEdit();self.a_text.setPlaceholderText('Hasil ekstraksi dari kotak A')
        self.a_text.setMaximumHeight(76);self.a_text.setMinimumHeight(53)
        right_l.addWidget(self.a_text)
        right_l.addWidget(QLabel('TEKS B  ·  dapat dikoreksi'))
        self.b_text = QPlainTextEdit();self.b_text.setPlaceholderText('Hasil ekstraksi dari kotak B')
        self.b_text.setMaximumHeight(76);self.b_text.setMinimumHeight(53)
        right_l.addWidget(self.b_text)
        self.quality_a = QLabel('Kualitas ekstraksi A: belum diperiksa')
        self.quality_b = QLabel('Kualitas ekstraksi B: belum diperiksa')
        for label in (self.quality_a, self.quality_b):
            label.setWordWrap(True)
            label.setStyleSheet('font-size: 10px; color: #6B4C1C;')
            right_l.addWidget(label)
        self.ocr_both = QPushButton('↻  Perbaiki Pembacaan Otomatis')
        self.ocr_both.setToolTip('Baca ulang kedua area. Bila OCR awal tidak jelas, lanjut otomatis dengan mode alternatif.')
        right_l.addWidget(self.ocr_both)
        self.ocr_note = QLabel('Memeriksa kedua area, mencoba OCR alternatif hanya bila diperlukan. Konfirmasi sebelum menyimpan koreksi.')
        self.ocr_note.setWordWrap(True)
        self.ocr_note.setStyleSheet('font-size: 10px; color: #596575;')
        right_l.addWidget(self.ocr_note)
        self.find = QPushButton('⌕  Cari Otomatis di PDF B')
        self.find.hide()  # finding the counterpart is automatic on area selection
        self.auto_note = QLabel('Klik parameter: cari koordinat A/B + OCR otomatis, tanpa mengubah Tahap 1.')
        self.auto_note.setWordWrap(True)
        self.auto_note.setStyleSheet('font-size: 10px; color: #536273;')
        right_l.addWidget(self.auto_note)
        self.ocr_suggestion_a = QLabel('OCR A: —')
        self.ocr_suggestion_b = QLabel('OCR B: —')
        for label in (self.ocr_suggestion_a, self.ocr_suggestion_b):
            label.setWordWrap(True)
            label.setStyleSheet('font-size: 10px; color: #44546A;')
            label.hide()  # avoid showing verbose OCR dumps in inspector
        use_ocr = QHBoxLayout()
        self.use_ocr_a = QPushButton('Gunakan OCR A')
        self.use_ocr_b = QPushButton('Gunakan OCR B')
        self.use_ocr_a.setEnabled(False)
        self.use_ocr_b.setEnabled(False)
        use_ocr.addWidget(self.use_ocr_a); use_ocr.addWidget(self.use_ocr_b)
        # Buttons kept as internal compatibility hooks; the user sees one recovery button.
        self.use_ocr_a.hide();self.use_ocr_b.hide()
        self.retry_auto = QPushButton('↻  Analisis Ulang Parameter A/B')
        self.retry_auto.hide()
        self.candidate_heading = QLabel('KANDIDAT ALTERNATIF PDF B')
        self.candidate_heading.hide()
        self.choice = QListWidget()
        self.choice.setMinimumHeight(58)
        self.choice.hide()  # candidate selection continues internally; manual box remains available
        self.area_info = QLabel('A: —\nB: —')
        self.area_info.setWordWrap(True)
        self.area_info.setStyleSheet('font-size: 10px; color: #626C79;')
        right_l.addWidget(self.area_info)
        self.confirm = QPushButton('✓  Konfirmasi & Perbarui Tahap 1')
        self.confirm.setObjectName('primary')
        right_l.addWidget(self.confirm)

        right_l = right_l_original
        right_l.addWidget(self._collapsible('INSPECTOR VALIDASI', inspector, True))
        right_l.addStretch(1)
        sidebar_scroll.setWidget(sidebar_root)
        sidebar_l.addWidget(sidebar_scroll, 1)
        self.main_split.addWidget(self.sidebar)
        self.main_split.setStretchFactor(0, 1)
        self.main_split.setStretchFactor(1, 0)
        self.main_split.setSizes([1070, 420])
        self.docs_split.setSizes([530, 530])

        statusrow = QHBoxLayout()
        self.status = QLabel('Buka parameter. Gunakan Berikutnya untuk verifikasi tanpa perubahan; konfirmasi jika ada koreksi.')
        self.status.setWordWrap(True)
        self.status.setStyleSheet('color: #495363;')
        statusrow.addWidget(self.status, 1)
        self.summary = QLabel('0 parameter')
        self.summary.setStyleSheet('font-weight: 700; color: #991B2B;')
        statusrow.addWidget(self.summary)
        root.addLayout(statusrow)

    def _setup_crop(self, label):
        label.setMinimumHeight(59);label.setMaximumHeight(88)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet('background: #F6F7F9; border: 1px solid #DCE0E5; border-radius: 4px; color: #657080;')
        label.setScaledContents(False)
        label.setWordWrap(True)

    def _connect_events(self):
        self.a.selected.connect(lambda item:self.on_select('A',item))
        self.b.selected.connect(lambda item:self.on_select('B',item))
        self.a.preview_changed.connect(lambda item: self._preview_mirrored('A', item))
        self.b.preview_changed.connect(lambda item: self._preview_mirrored('B', item))
        self.field_list.currentTextChanged.connect(self.change_field)
        self.parameter_search.textChanged.connect(self._filter_parameters)
        self.field_list.itemChanged.connect(self._parameter_check_changed)
        self.a.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.b.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.a.canvas.customContextMenuRequested.connect(lambda point: self._open_parameter_menu('A', point))
        self.b.canvas.customContextMenuRequested.connect(lambda point: self._open_parameter_menu('B', point))
        self.find.clicked.connect(self.auto_find)
        self.retry_auto.clicked.connect(lambda: self._start_auto_verification(force=True))
        self.use_ocr_a.clicked.connect(lambda: self._use_auto_ocr('A'))
        self.use_ocr_b.clicked.connect(lambda: self._use_auto_ocr('B'))
        self.confirm.clicked.connect(self.validate)
        self.save.clicked.connect(self.export_json)
        self.choice.currentRowChanged.connect(self.pick_candidate)
        self.prev_field.clicked.connect(lambda:self._navigate(-1))
        self.next_field.clicked.connect(self.verify_and_next)
        self.a_text.textChanged.connect(self._mark_dirty)
        self.b_text.textChanged.connect(self._mark_dirty)
        self.zoom_crop_a.clicked.connect(lambda:self._open_crop('A'))
        self.zoom_crop_b.clicked.connect(lambda:self._open_crop('B'))
        self.ocr_both.clicked.connect(self._recover_both)

    def _filter_parameters(self, phrase):
        phrase = phrase.strip().casefold()
        for i in range(self.field_list.count()):
            item = self.field_list.item(i)
            item.setHidden(phrase not in item.text().casefold())

    def _parameter_check_changed(self, item):
        field = item.text()
        checked = item.checkState() == Qt.CheckState.Checked
        self.annotation_visibility[field] = checked
        item.setToolTip(('Tampilkan penanda' if checked else 'Sembunyikan penanda') + ': ' + field)
        self._refresh_persistent_overlays()
        # Shared state with Hasil & Ekspor. Never remove an extraction or finding.
        callback = getattr(self.parent(), 'stage2_annotation_changed', None)
        if callable(callback):
            callback(field, checked, self.annotation_regions.get(field))

    def _remember_annotation(self, field, side, page, rect):
        if not field or rect is None:
            return
        rect = fitz.Rect(rect)
        if rect.is_empty or rect.is_infinite:
            return
        self.annotation_regions.setdefault(field, {})[side] = {
            'page': int(page), 'rect_pdf': [rect.x0, rect.y0, rect.x1, rect.y1]
        }
        self._refresh_persistent_overlays()
        callback = getattr(self.parent(), 'stage2_annotation_changed', None)
        if callable(callback):
            callback(field, self.annotation_visibility.get(field, True), self.annotation_regions.get(field))

    def _refresh_persistent_overlays(self):
        current = self.field_list.currentItem()
        active = current.text() if current else ''
        for side, canvas in (('A', self.a.canvas), ('B', self.b.canvas)):
            canvas.setProperty('active_field', active)
            canvas.overlays = {
                name: {'page': value[side]['page'], 'rect': fitz.Rect(value[side]['rect_pdf'])}
                for name, value in self.annotation_regions.items()
                if self.annotation_visibility.get(name, True) and side in value
            }
            canvas.update()

    def _open_parameter_menu(self, side, local_point):
        """Right-click either PDF: searchable, visibly checkable parameter list."""
        canvas = self.a.canvas if side == 'A' else self.b.canvas
        menu = QMenu(self)
        action = QWidgetAction(menu)
        wrapper = QWidget(menu)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(7, 7, 7, 7)
        search = QLineEdit(wrapper)
        search.setPlaceholderText('Cari parameter…')
        layout.addWidget(search)
        options = QListWidget(wrapper)
        options.setMinimumWidth(285)
        options.setMinimumHeight(290)
        for i in range(self.field_list.count()):
            source = self.field_list.item(i)
            entry = QListWidgetItem(source.text())
            entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            entry.setCheckState(source.checkState())
            options.addItem(entry)
        layout.addWidget(options)
        action.setDefaultWidget(wrapper)
        menu.addAction(action)
        search.textChanged.connect(lambda q: [options.item(i).setHidden(q.casefold() not in options.item(i).text().casefold()) for i in range(options.count())])
        def chosen(item):
            for i in range(self.field_list.count()):
                primary = self.field_list.item(i)
                if primary.text() == item.text():
                    primary.setCheckState(item.checkState())
                    if item.checkState() == Qt.CheckState.Checked:
                        self.field_list.setCurrentRow(i)
                    menu.close()
                    break
        options.itemClicked.connect(chosen)
        # Clicking a checkbox updates the sidebar checklist; clicking the name
        # also navigates. No new region is committed by a menu operation.
        menu.exec(canvas.mapToGlobal(local_point))

    def _recover_both(self):
        """One visible recovery button: re-locate and OCR both, then suggest usable
        candidates. Existing Stage-1 values stay intact until confirmation."""
        field_item = self.field_list.currentItem()
        if field_item is None:
            return
        self.ocr_note.setText('Pemulihan otomatis sedang berjalan untuk A dan B…')
        self._recover_requested = True
        self._start_auto_verification(force=True)

    def _quality_status(self, side, result):
        label = self.quality_a if side == 'A' else self.quality_b
        q = result.get('quality') or text_quality(result.get('text', ''))
        if q['suspicious']:
            explanation = (f"{q['replacement_chars']} karakter �" if q['replacement_chars'] else
                           'hasil kosong / karakter kontrol')
            label.setText(f'⚠ Area {side}: {explanation}; periksa crop atau coba OCR region.')
        else:
            label.setText(f'Area {side}: karakter native tidak menunjukkan kerusakan jelas (tetap periksa visual).')

    def ocr_region(self, side):
        item = self.selection.get(side)
        if not item:
            QMessageBox.information(self, 'Kotak belum dipilih',
                                    f'Gambar atau pilih kotak PDF {side} terlebih dahulu.')
            return
        doc = self.ref_doc if side == 'A' else self.exam_doc
        widget = self.a_text if side == 'A' else self.b_text
        native = extract_region(doc[item['page']], item['rect'], self.profile)
        self._quality_status(side, native)
        try:
            options = read_region_candidates(doc[item['page']], item['rect'])
        except (OCRError, ValueError, RuntimeError, OSError) as exc:
            QMessageBox.warning(self, 'OCR offline tidak tersedia / gagal', str(exc) +
                '\n\nPastikan Tesseract dan eng.traineddata tersedia. Teks masih bisa dikoreksi manual.')
            return
        if not options:
            QMessageBox.information(self, 'OCR tidak menemukan teks',
                                    'Tidak ada alternatif yang terbaca. Perbesar area seleksi atau koreksi manual.')
            return
        display = [f"{i+1}. {x['variant']} · PSM {x['psm']} · skor OCR {x['confidence']:.0f} · " +
                   x['text'].replace('\n',' ')[:90] for i,x in enumerate(options)]
        selected, accepted = QInputDialog.getItem(self, f'Alternatif OCR Area {side}',
            'Pilih kandidat. Skor OCR bukan jaminan kebenaran; cocokkan dengan crop PDF.',
            display, 0, False)
        if not accepted:
            return
        chosen = options[display.index(selected)]
        widget.setPlainText(chosen['text'])
        self._ocr_choice[side] = chosen
        self._dirty = True
        self.status.setText(f"Area {side}: alternatif OCR ({chosen['variant']}, PSM {chosen['psm']}) dipilih. "
                            'Periksa dan konfirmasi sebelum memperbarui Tahap 1.')
        self.ocr_note.setText(f"Area {side}: OCR {chosen['variant']} / PSM {chosen['psm']}, "
                              f"skor {chosen['confidence']:.0f}; belum dikonfirmasi.")

    def _mark_dirty(self):
        self._dirty = True
        field = self.field_list.currentItem()
        if field is not None and field.text() in self.records:
            self.result_tag.setText('BERUBAH · KONFIRMASI ULANG')
            self.result_tag.setStyleSheet('background: #FFF1D6; color: #8B5600; padding: 5px; border-radius: 4px; font-weight: 700;')

    def _navigate(self, offset):
        index = self.field_list.currentRow() + offset
        if 0 <= index < self.field_list.count():
            self.field_list.setCurrentRow(index)

    def _set_tag(self, status):
        palette = {
            'MATCH': ('#E1F3E8','#12673A'),
            'MISMATCH': ('#FFE7E7','#9A1F2D'),
            'PERLU_VERIFIKASI': ('#FFF1D6','#885600'),
            'KANDIDAT': ('#FFF1D6','#885600'),
            'BELUM DIPERIKSA': ('#EEF0F3','#485363'),
            'VERIFIED_UNCHANGED': ('#E1F3E8','#12673A'),
        }
        bg,fg = palette.get(status, ('#EEF0F3','#485363'))
        self.result_tag.setText(status.replace('_',' '))
        self.result_tag.setStyleSheet(f'background: {bg}; color: {fg}; padding: 5px; border-radius: 4px; font-weight: 700;')

    def _refresh_checklist(self):
        count = self.field_list.count()
        done = len(self.records)
        self.progress.setRange(0, max(1,count));self.progress.setValue(done)
        self.progress_text.setText(f'{done} / {count} parameter dikonfirmasi')
        self.summary.setText(f'Terverifikasi: {done}/{count}')
        for i in range(count):
            item = self.field_list.item(i)
            status = self.records.get(item.text(),{}).get('status')
            # Preserve raw field names for mapping; signal/currentText uses item.text().
            item.setForeground(QColor('#147346' if status in ('MATCH','VERIFIED_UNCHANGED') else '#AF2739' if status=='MISMATCH' else '#A76B12' if status else '#4A5564'))
            item.setToolTip(f'{item.text()} — {status or "Belum dikonfirmasi"}')

    def _show_crop(self, side):
        label = self.crop_a if side == 'A' else self.crop_b
        selection = self.selection[side]
        if selection is None:
            label.setPixmap(QPixmap())
            label.setText('Pilih kotak pada PDF ' + side)
            return
        doc = self.ref_doc if side == 'A' else self.exam_doc
        page = doc[selection['page']]
        clip = fitz.Rect(selection['rect']) & page.rect
        if clip.is_empty or clip.width < 1 or clip.height < 1:
            label.setPixmap(QPixmap());label.setText('Area kosong');return
        # Large zoom in source image, then fit aspect ratio into inspector preview.
        scale = max(1.5,min(4.0,350.0/max(clip.width,1)))
        pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=clip,alpha=False)
        src = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
        view = QPixmap.fromImage(src)
        label.setText('')
        label.setPixmap(view.scaled(max(170,label.width()-8),70,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def _open_crop(self, side):
        """Show the exact selected PDF region at high resolution, not an upscaled thumbnail."""
        selected = self.selection[side]
        if not selected:
            QMessageBox.information(self,'Belum ada area',f'Seleksi area PDF {side} terlebih dahulu.')
            return
        doc = self.ref_doc if side == 'A' else self.exam_doc
        page = doc[selected['page']]
        rect = fitz.Rect(selected['rect']) & page.rect
        if rect.is_empty:return
        zoom = max(2.0,min(5.0,700/max(rect.width,1)))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),clip=rect,alpha=False)
        src = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
        dlg = QDialog(self)
        dlg.setWindowTitle(f'DocMatch — Crop PDF {side} · Halaman {selected["page"]+1}')
        dlg.resize(780,360)
        layout = QVBoxLayout(dlg)
        instructions = QLabel('Pembesaran area terpilih; edit nilai teks pada Inspector Validasi.')
        layout.addWidget(instructions)
        scroll = QScrollArea()
        crop = QLabel()
        crop.setPixmap(QPixmap.fromImage(src))
        scroll.setWidget(crop)
        layout.addWidget(scroll,1)
        close = QPushButton('Tutup')
        close.clicked.connect(dlg.accept)
        layout.addWidget(close)
        dlg.exec()

    def _refresh_area_info(self):
        lines=[]
        for side in ('A','B'):
            selected = self.selection[side]
            if selected:
                r = selected['rect']
                source = self._source_kind[side] or 'manual'
                lines.append(f'{side}: hal {selected["page"]+1}  |  ({r.x0:.0f}, {r.y0:.0f})–({r.x1:.0f}, {r.y1:.0f})  |  {source}')
            else: lines.append(f'{side}: belum dipilih')
        self.area_info.setText('\n'.join(lines))
        self._show_crop('A');self._show_crop('B')

    def closeEvent(self, event):
        if self._batch_task is not None:
            self._batch_task.cancelled.set()
        self._auto_generation += 1  # ignore results arriving after close
        self._auto_pool.waitForDone(10000)
        self.ref_doc.close();self.exam_doc.close()
        super().closeEvent(event)

    def _page_one_fields(self):
        """Include only fields with a defined region on page index 0."""
        try:
            from waybill_rules import _profile_cells
            cells = _profile_cells(self.profile)
            return [f for f in self._field_names if any(r[0] == 0 for r in cells.get(f, []))]
        except (ImportError, ValueError, TypeError, KeyError):
            # Don't automatically OCR unspecified fields when page mapping is unknown.
            return []

    def _start_page_one_batch(self):
        fields = self._page_one_fields()
        self._batch_total = len(fields)
        self._batch_done = 0
        self.batch_progress.setRange(0, max(1, len(fields)))
        self.batch_progress.setValue(0)
        if not fields:
            self.batch_status.setText('Tidak ada template halaman 1; pilih parameter secara manual.')
            return
        self.batch_status.setText(f'Analisis otomatis halaman 1: 0/{len(fields)} parameter…')
        # The thread pool serializes work for i5/8GB; current user selection stays interactive.
        batch = BatchPageOneTask(fields, self.reference_path, self.examined_path,
                                  self.profile, self.stage1_fields)
        self._batch_task = batch
        batch.signals.field_ready.connect(self._batch_field_ready)
        batch.signals.complete.connect(self._batch_complete)
        self._auto_pool.start(batch)

    def _batch_field_ready(self, field, payload, done, total):
        if self._batch_task is None:
            return
        self._batch_results[field] = payload
        for side in ('A', 'B'):
            info = payload.get('sides', {}).get(side, {})
            if info.get('found') and info.get('rect') is not None:
                # A manual edit or confirmed record always wins over batch candidates.
                if side not in self.annotation_regions.get(field, {}):
                    self._remember_annotation(field, side, info['page'], info['rect'])
        self._auto_cache.setdefault(field, payload)
        self._batch_done = done
        self.batch_progress.setValue(done)
        for i in range(self.field_list.count()):
            entry = self.field_list.item(i)
            if entry.text() == field:
                n = sum(bool(payload.get('sides', {}).get(side, {}).get('found')) for side in ('A', 'B'))
                entry.setToolTip('Analisis otomatis halaman 1: ' +
                                 ('A/B ditemukan; periksa hasil OCR' if n == 2 else 'Area belum lengkap; perlu koreksi manual'))
                break
        complete_regions = sum(all(v.get('found') for v in result.get('sides', {}).values())
                               and len(result.get('sides', {})) == 2
                               for result in self._batch_results.values())
        self.batch_status.setText(f'Analisis halaman 1: {done}/{total} · pasangan area {complete_regions} · konfirmasi tetap manual')
        current = self.field_list.currentItem()
        if current and current.text() == field and not self._dirty and not self.records.get(field):
            self._auto_generation += 1
            self._apply_auto_result(self._auto_generation, field, payload)

    def _batch_complete(self, total):
        self.batch_status.setText(f'Analisis halaman 1 selesai: {total} parameter. Klik parameter untuk meninjau; hasil Tahap 1 tidak berubah.')
        self._batch_task = None

    @staticmethod
    def _mirror_rect(source_rect, source_page, target_page):
        """Same proportional x/y/w/h in page coordinates; safe across page sizes."""
        src = source_page.rect
        dst = target_page.rect
        if not src.width or not src.height:
            return fitz.Rect(dst)
        rx0 = (source_rect.x0-src.x0)/src.width
        ry0 = (source_rect.y0-src.y0)/src.height
        rx1 = (source_rect.x1-src.x0)/src.width
        ry1 = (source_rect.y1-src.y0)/src.height
        return fitz.Rect(dst.x0+rx0*dst.width, dst.y0+ry0*dst.height,
                         dst.x0+rx1*dst.width, dst.y0+ry1*dst.height) & dst

    def change_field(self, field):
        if not field:return
        self._auto_generation += 1
        self._dirty = False
        self._auto_review_required = False
        self._auto_ocr_suggestions = {'A': None, 'B': None}
        self._recover_requested = False
        for label in (self.ocr_suggestion_a, self.ocr_suggestion_b):
            label.setText('OCR: —')
        self.use_ocr_a.setEnabled(False); self.use_ocr_b.setEnabled(False)
        self.active_field.setText(field)
        rec = self.records.get(field)
        self.selection={'A':None,'B':None};self._confirmed={'A':False,'B':False}
        self._source_kind={'A':'','B':''}
        self._ocr_choice={'A':None,'B':None}
        self.candidates=[]
        self.choice.blockSignals(True);self.choice.clear();self.choice.blockSignals(False)
        self.a.canvas.region=None;self.b.canvas.region=None
        self._refresh_persistent_overlays()
        self.a.canvas.update();self.b.canvas.update()
        self.a_text.blockSignals(True);self.b_text.blockSignals(True)
        self.a_text.clear();self.b_text.clear()
        self.quality_a.setText('Kualitas ekstraksi A: belum diperiksa')
        self.quality_b.setText('Kualitas ekstraksi B: belum diperiksa')
        self.ocr_note.setText('Jika hasil lama benar, klik Berikutnya. Gunakan pemulihan hanya untuk pembacaan yang rusak.')
        if rec and rec.get('A') and rec.get('B'):
            for side,viewer,widget in [('A',self.a,self.a_text),('B',self.b,self.b_text)]:
                part = rec[side]
                viewer.show_region(part['page'],fitz.Rect(part['rect_pdf']))
                self.selection[side]={'page':part['page'],'rect':fitz.Rect(part['rect_pdf'])}
                self._remember_annotation(field, side, part['page'], part['rect_pdf'])
                self._source_kind[side]=part.get('selection_method','saved')
                self._confirmed[side]=True
                widget.setPlainText(part['text_final'])
            self.status.setText('Hasil tahap 2 tersimpan. Kamu dapat memperbaiki area dan konfirmasi ulang.')
            self._set_tag(rec['status'])
        else:
            self.status.setText(f'{field}: tinjau Tahap 1, atau gambar kotak PDF A jika perlu koreksi.')
            self._set_tag('BELUM DIPERIKSA')
        self.a_text.blockSignals(False);self.b_text.blockSignals(False)
        if not rec or rec.get('outcome') == 'retain_stage1':
            initial = self.stage1_fields.get(field, {})
            base_status = initial.get('status', 'MATCH')
            self.status.setText(f'{field} · Tahap 1: {base_status}. Bila hasil Tahap 1 benar, klik Berikutnya tanpa menggambar kotak.')
            # Stage-one data is read-only until user explicitly modifies and confirms.
            self.a_text.setPlainText(initial.get('reference_text', ''))
            self.b_text.setPlainText(initial.get('examined_text', ''))
            self._dirty = False
            if rec and rec.get('outcome') == 'retain_stage1':
                self._set_tag('VERIFIED_UNCHANGED')
                self.status.setText(f'{field}: hasil Tahap 1 sudah diverifikasi tanpa perubahan.')
        self._refresh_area_info()
        # Stage 2 automatically inspects both document regions on parameter selection.
        # Never mutate existing confirmed records just because the user revisits a field.
        if not (rec and rec.get('outcome') == 'override_stage1'):
            self._start_auto_verification()

    def _start_auto_verification(self, force=False):
        item = self.field_list.currentItem()
        if item is None:
            return
        field = item.text()
        if not force and self.records.get(field, {}).get('outcome') == 'override_stage1':
            return
        if not force and self._batch_task is not None and field in self._page_one_fields() and field not in self._auto_cache:
            self.auto_note.setText('Batch otomatis halaman 1 sedang menganalisis parameter ini; hasil akan ditampilkan segera setelah siap.')
            return
        self._auto_generation += 1
        generation = self._auto_generation
        if force:
            self._auto_cache.pop(field, None)
        if field in self._auto_cache:
            self._apply_auto_result(generation, field, self._auto_cache[field])
            return
        self._auto_loading = True
        self.auto_note.setText('Mendeteksi layout dan OCR region A/B di latar belakang…')
        self.status.setText(f'{field}: sedang mencari lokasi A/B dan membaca ulang area; hasil Tahap 1 belum berubah.')
        hints = dict(self.stage1_fields.get(field, {}))
        if self._source_kind.get('A') == 'manual':
            hints['examined_text'] = self.a_text.toPlainText().strip()
        elif self._source_kind.get('B') == 'manual':
            hints['reference_text'] = self.b_text.toPlainText().strip()
        task = AutoLocateTask(generation, field, self.reference_path, self.examined_path,
                              self.profile, hints)
        self._auto_workers[generation] = task
        task.signals.finished.connect(self._auto_finished)
        self._auto_pool.start(task)

    def _auto_finished(self, generation, field, payload):
        self._auto_workers.pop(generation, None)
        self._auto_cache[field] = payload
        if generation != self._auto_generation or self.field_list.currentItem() is None:
            return
        if self.field_list.currentItem().text() != field:
            return
        self._apply_auto_result(generation, field, payload)

    def _apply_auto_result(self, generation, field, payload):
        if generation != self._auto_generation or (self._dirty and not any(self._source_kind.get(x)=='manual' for x in ('A','B'))):
            return  # never overwrite text edits with late worker results
        self._auto_loading = False
        valid_sides = []
        requires_review = []
        self._auto_ocr_suggestions = {'A': None, 'B': None}
        self._auto_review_required = False
        for side, viewer, widget in (('A', self.a, self.a_text), ('B', self.b, self.b_text)):
            info = payload.get('sides', {}).get(side, {})
            if self._source_kind.get(side) == 'manual':
                valid_sides.append(side)
                continue  # never override the region the user just drew
            if not info.get('found'):
                requires_review.append(side)
                continue
            rect = fitz.Rect(info['rect'])
            self.selection[side] = {'page': info['page'], 'rect': rect}
            self._remember_annotation(field, side, info['page'], rect)
            self._source_kind[side] = 'auto_candidate'
            self._confirmed[side] = False
            viewer.show_region(info['page'], refined_highlight_rect(rect, info.get('native') or {}), candidate=True)
            native = info.get('native') or {}
            options = info.get('ocr') or []
            native_text = native.get('text', '')
            # OCR has to be intentionally reviewed; use Stage-1 text as safe default.
            original = self.stage1_fields.get(field, {})
            value = original.get('reference_text' if side == 'A' else 'examined_text', '')
            if not value:
                value = native_text or (options[0]['text'] if options else '')
            # A recovery click may fill the editable preview when old text is corrupt.
            # Require plausible OCR: no replacement chars, adequate OCR score, no
            # obvious unrelated cargo/clauses content for a different field.
            if self._recover_requested and options:
                candidate = options[0]
                ocr_value = candidate.get('text', '').strip()
                unrelated = ('FREIGHT PREPAID', 'SHIPPER\'S LOAD', 'CONT TOT. TARE',
                             'CLAUSES AS PER', 'CARGO WEIGHT', 'TOTAL: TWO THOUSAND')
                unrelated = any(word in ocr_value.upper() for word in unrelated)
                unreliable = (not value.strip() or text_quality(value)['suspicious']
                              or '\ufffd' in value)
                if (unreliable and not unrelated and len(ocr_value) >= 3
                    and candidate.get('confidence', 0) >= 65
                    and not text_quality(ocr_value)['suspicious']):
                    value = ocr_value
                    self._ocr_choice[side] = dict(candidate, auto_preview=True)
                    requires_review.append(side)
            widget.blockSignals(True)
            widget.setPlainText(value)
            widget.blockSignals(False)
            self._quality_status(side, native)
            suggestion_label = self.ocr_suggestion_a if side == 'A' else self.ocr_suggestion_b
            suggestion_btn = self.use_ocr_a if side == 'A' else self.use_ocr_b
            suggestion_btn.setEnabled(bool(options))
            if options:
                top = options[0]
                self._auto_ocr_suggestions[side] = top
                pass_name = 'OCR fallback' if info.get('ocr_fallback_used') else 'OCR awal'
                suggestion_label.setText(f"{pass_name} {side} [{top['confidence']:.0f}]: " +
                                         top['text'].replace('\n', ' ')[:115])
                self._ocr_choice[side] = dict(top, auto_suggested=True)
                self.ocr_note.setText('OCR A+B otomatis; mode kedua dijalankan bila hasil awal tidak meyakinkan. '
                                      'Hasil alternatif tidak langsung mengganti data: '
                                      'periksa crop dan koreksi teks jika diperlukan.')
                if text_quality(native_text)['suspicious']:
                    requires_review.append(side)
                if value and normalize_text(value) != normalize_text(top['text']):
                    requires_review.append(side)
            else:
                suggestion_label.setText(f'OCR {side}: tidak tersedia / tidak menemukan teks')
            if info.get('ocr_error'):
                requires_review.append(side)
            valid_sides.append(side)
        if not any(self._source_kind.get(x)=='manual' for x in ('A','B')):
            self._dirty = False
        self._recover_requested = False
        self._auto_review_required = bool(requires_review)
        self._set_tag('KANDIDAT' if valid_sides else 'BELUM DIPERIKSA')
        self._refresh_area_info()
        # Keep OCR proposals out of the Stage-1 values; explicitly warn when OCR
        # appears unrelated to the field (e.g. clause text for Notify Party).
        bad_ocr = []
        for side in ('A','B'):
            suggestion = self._auto_ocr_suggestions.get(side)
            if not suggestion: continue
            actual = self.stage1_fields.get(field, {}).get('reference_text' if side=='A' else 'examined_text','')
            raw = suggestion.get('text','')
            if actual and len(raw)>35 and difflib.SequenceMatcher(None,_normalize(actual)[:140],_normalize(raw)[:140]).ratio()<.18:
                bad_ocr.append(side)
        if bad_ocr:
            self.ocr_note.setText('OCR menghasilkan teks yang mungkin salah wilayah (' + ', '.join(bad_ocr) + '). Periksa crop / koreksi kotak; nilai lama tidak diganti.')
        else:
            self.ocr_note.setText('OCR A/B selesai. Periksa crop dan teks; konfirmasi hanya jika ada koreksi.')
        if len(valid_sides) == 2:
            self.auto_note.setText('Area A/B ditemukan; OCR bertingkat selesai. '
                                   'Periksa kedua crop. Jika benar tanpa koreksi, klik Berikutnya.')
            self.status.setText(f'{field}: A/B ditemukan. OCR kandidat siap diperiksa; Tahap 1 belum berubah.'
                                + (' Periksa karakter/kotak yang meragukan.' if requires_review else ''))
        else:
            self.auto_note.setText('Lokasi belum ditemukan pada ' + ', '.join(x for x in ('A','B') if x not in valid_sides)
                                   + '. Buat seleksi manual pada dokumen tersebut.')
            self.status.setText(f'{field}: deteksi lokasi tidak lengkap. Seleksi kotak secara manual.')

    def _use_auto_ocr(self, side):
        item = (getattr(self, '_auto_ocr_suggestions', {}) or {}).get(side)
        if not item:
            return
        widget = self.a_text if side == 'A' else self.b_text
        widget.setPlainText(item['text'])
        self._ocr_choice[side] = dict(item, accepted_for_review=True)
        self._dirty = True
        self.status.setText(f'OCR {side} dipilih. Periksa crop, lalu Konfirmasi & Perbarui Tahap 1.')

    def verify_and_next(self):
        # One-click carry-forward: keep comparison data and log verification.
        current = self.field_list.currentItem()
        if current is None:return
        field = current.text()
        old = self.records.get(field)
        if self._auto_review_required:
            response = QMessageBox.question(self, 'Periksa perbedaan hasil OCR',
                'OCR otomatis menemukan kandidat yang berbeda dari hasil Tahap 1, atau pembacaan native tidak jelas. '
                'Apakah hasil Tahap 1 sudah Anda periksa secara visual dan tetap ingin mempertahankannya?')
            if response != QMessageBox.StandardButton.Yes:
                return
            self._auto_review_required = False
        if self._dirty:
            QMessageBox.information(self, 'Perubahan belum dikonfirmasi',
                'Ada teks yang diubah. Klik Konfirmasi & Perbarui Tahap 1 dahulu, atau kembalikan teks semula.')
            return
        if not old:
            original = self.stage1_fields.get(field, {})
            if original.get('status') == 'PERLU_VERIFIKASI':
                QMessageBox.warning(self, 'Tahap 1 belum dapat dipastikan',
                    'Tahap 1 belum berhasil membaca parameter ini. Seleksi area pada kedua PDF dan konfirmasi hasilnya; tidak boleh langsung diloloskan.')
                return
            record = {'field_id': field, 'status': 'VERIFIED_UNCHANGED', 'outcome': 'retain_stage1',
                'stage1_status': original.get('status','MATCH'),
                'confirmed_at': datetime.now(timezone.utc).isoformat(),
                'A': None, 'B': None}
            self.records[field] = record
            self._set_tag('VERIFIED_UNCHANGED')
            self._refresh_checklist()
            self.status.setText(f'{field}: hasil Tahap 1 dipertahankan, verifikasi tanpa perubahan selesai.')
            callback = getattr(self.parent(), 'apply_stage2_record', None)
            if callable(callback): callback(record)
        self._navigate(1)

    def _preview_mirrored(self, source, item):
        """Live geometry overlay only; OCR/extraction runs on mouse release."""
        if not self.sync_coordinates.isChecked():
            return
        origin_doc = self.ref_doc if source == 'A' else self.exam_doc
        other_doc = self.exam_doc if source == 'A' else self.ref_doc
        if item['page'] >= len(other_doc):
            return
        other = self.b if source == 'A' else self.a
        rect = self._mirror_rect(item['rect'], origin_doc[item['page']], other_doc[item['page']])
        other.canvas.set_region(item['page'], rect, candidate=True)

    def on_select(self, side, item):
        """Manual change mirrors normalized page geometry; each side reads its own text."""
        self._auto_generation += 1
        self._dirty = True
        self.selection[side] = item
        current = self.field_list.currentItem()
        field = current.text() if current else ''
        self._remember_annotation(field, side, item['page'], item['rect'])
        self._confirmed[side] = True
        self._source_kind[side] = 'manual'
        doc = self.ref_doc if side == 'A' else self.exam_doc
        target_text = self.a_text if side == 'A' else self.b_text
        extracted = extract_region(doc[item['page']], item['rect'], self.profile)
        target_text.setPlainText(extracted['text'])
        self._ocr_choice[side] = None
        self._quality_status(side, extracted)
        other = 'B' if side == 'A' else 'A'
        if self.sync_coordinates.isChecked():
            opposite_doc = self.exam_doc if other == 'B' else self.ref_doc
            if item['page'] < len(opposite_doc):
                mirrored = self._mirror_rect(item['rect'], doc[item['page']],
                                             opposite_doc[item['page']])
                self.selection[other] = {'page': item['page'], 'rect': mirrored}
                self._remember_annotation(field, other, item['page'], mirrored)
                self._confirmed[other] = False  # same geometry does not imply correct field
                self._source_kind[other] = 'mirrored_unverified'
                other_view = self.b if other == 'B' else self.a
                other_view.show_region(item['page'], mirrored, candidate=True)
                other_result = extract_region(opposite_doc[item['page']], mirrored, self.profile)
                other_widget = self.b_text if other == 'B' else self.a_text
                other_widget.setPlainText(other_result['text'])
                self._quality_status(other, other_result)
                self._ocr_choice[other] = None
                self.status.setText('Kotak A/B disinkronkan pada posisi relatif sama. Periksa kedua crop: layout dapat berbeda. Konfirmasi sebelum memperbarui Tahap 1.')
            else:
                self.status.setText('Halaman pasangan tidak ada. Pilih area pasangan secara manual.')
        else:
            self.status.setText(f'Area PDF {side} ditandai; mencari parameter pada PDF {other}…')
            if self._source_kind.get(other) != 'manual':
                self._start_auto_verification(force=True)
        self._set_tag('BELUM DIPERIKSA')
        self._refresh_area_info()

    def auto_find(self):
        self._auto_generation += 1
        if not self.selection['A']:
            QMessageBox.information(self,'Area sumber belum dipilih','Gambar kotak di PDF A terlebih dahulu.')
            return
        field=self.field_list.currentItem().text()
        self.candidates=find_candidates(self.exam_doc,field,self.a_text.toPlainText(),self.profile)
        self.choice.blockSignals(True);self.choice.clear()
        for item in self.candidates:
            text=item['extraction']['text'].replace('\n',' ')[:52] or '[teks tidak terbaca]'
            self.choice.addItem(f"Hal {item['page']+1} · {item['reason']} · {text}")
        self.choice.blockSignals(False)
        if self.candidates:
            self.choice.setCurrentRow(0)
            self.status.setText('Kotak kuning = kandidat otomatis. Konfirmasi hanya setelah area dan teks diperiksa.')
        else:
            self.selection['B']=None;self._confirmed['B']=False
            self._source_kind['B']=''
            self.b.canvas.region=None;self.b.canvas.update();self.b_text.clear()
            self.status.setText('Kandidat otomatis tidak ditemukan. Gambar kotak pada PDF B secara manual.')
            self._refresh_area_info()

    def pick_candidate(self,index):
        if not (0 <= index < len(self.candidates)):return
        item=self.candidates[index]
        self._dirty = True
        self.selection['B']={'page':item['page'],'rect':fitz.Rect(item['rect'])}
        self._confirmed['B']=False
        self._source_kind['B']='candidate'
        self.b.show_region(item['page'],item['rect'],candidate=True)
        self.b_text.setPlainText(item['extraction']['text'])
        self._ocr_choice['B']=None
        self._quality_status('B', item['extraction'])
        self._set_tag('KANDIDAT')
        self._refresh_area_info()

    def validate(self):
        self._auto_generation += 1
        if not self.selection['A'] or not self.selection['B']:
            QMessageBox.warning(self,'Kotak belum lengkap','Pilih area di PDF A dan PDF B terlebih dahulu.')
            return
        field=self.field_list.currentItem().text()
        if 'mirrored_unverified' in self._source_kind.values():
            confirmation = QMessageBox.question(self, 'Periksa koordinat sinkron',
                'Kotak pasangan disalin ke posisi relatif yang sama, bukan ditemukan dari label. '
                'Sudahkah kedua area dan isinya diperiksa secara visual?')
            if confirmation != QMessageBox.StandardButton.Yes:
                return
        a=self.selection['A'];b=self.selection['B']
        ex_a=extract_region(self.ref_doc[a['page']],a['rect'],self.profile)
        ex_b=extract_region(self.exam_doc[b['page']],b['rect'],self.profile)
        ta=self.a_text.toPlainText().strip();tb=self.b_text.toPlainText().strip()
        if not ta or not tb:
            answer=QMessageBox.question(self,'Teks belum dapat diverifikasi',
                'Salah satu nilai masih kosong. Simpan sebagai PERLU_VERIFIKASI?')
            if answer != QMessageBox.StandardButton.Yes:return
            status='PERLU_VERIFIKASI'
        else:
            if not ex_a['readable'] or not ex_b['readable']:
                approved = QMessageBox.question(self, 'Konfirmasi hasil koreksi manual',
                    'Teks PDF di salah satu area tidak dapat diekstrak secara andal. '
                    'Gunakan nilai yang Anda ketik sebagai hasil verifikasi manual?')
                if approved != QMessageBox.StandardButton.Yes: return
            status='MATCH' if normalize_text(ta)==normalize_text(tb) else 'MISMATCH'
        # Confirmation of a proposed candidate is an explicit user action.
        self.records[field]={'field_id':field,'status':status,'outcome':'override_stage1',
            'confirmed_at':datetime.now(timezone.utc).isoformat(),
            'A':{'page':a['page'],'rect_pdf':_rect_json(a['rect']),
                 'text_extracted':ex_a['text'],'text_final':ta,'source':ex_a['source'],
                 'selection_method':self._source_kind['A'] or 'manual',
                 'ocr_alternative':self._ocr_choice['A'], 'native_quality':ex_a.get('quality')},
            'B':{'page':b['page'],'rect_pdf':_rect_json(b['rect']),
                 'text_extracted':ex_b['text'],'text_final':tb,'source':ex_b['source'],
                 'selection_method':self._source_kind['B'] or 'manual',
                 'ocr_alternative':self._ocr_choice['B'], 'native_quality':ex_b.get('quality')}}
        self._confirmed={'A':True,'B':True}
        self._remember_annotation(field, 'A', a['page'], a['rect'])
        self._remember_annotation(field, 'B', b['page'], b['rect'])
        self.b.canvas.candidate=False;self.b.canvas.update()
        self._dirty=False
        self._set_tag(status)
        self.status.setText(f'{field}: {status}. Koreksi dipromosikan menjadi hasil aktif Tahap 1.')
        callback = getattr(self.parent(), 'apply_stage2_record', None)
        if callable(callback): callback(self.records[field])
        self._refresh_checklist()

    def export_json(self):
        import json
        if not self.records:
            QMessageBox.information(self,'Belum ada hasil','Konfirmasi minimal satu parameter dahulu.')
            return
        name,_=QFileDialog.getSaveFileName(self,'Simpan validasi tahap 2','docmatch_hybrid_validation.json','JSON (*.json)')
        if not name:return
        payload={'schema_version':2,'stage':'manual_validation_stage_2',
                 'reference_pdf':self.reference_path,'examined_pdf':self.examined_path,
                 'profile':self.profile,'field_count':len(self._field_names),
                 'records':list(self.records.values()),
                 'meaning':'Koreksi menggantikan hasil aktif Tahap 1; audit baseline tetap tersedia.'}
        Path(name).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        QMessageBox.information(self,'Tersimpan','Laporan validasi tahap 2 diekspor terpisah dari tahap 1.')
