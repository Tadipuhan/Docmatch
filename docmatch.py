"""DocMatch v0.2: local desktop visual document comparison."""
from __future__ import annotations
import sys, tempfile, shutil, json, difflib, re
from pathlib import Path
from dataclasses import asdict
import fitz
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QFont
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QFileDialog,QSplitter,QScrollArea,QListWidget,QListWidgetItem,QMessageBox,QComboBox,QFrame,QCheckBox)
from legacy_v01 import read_blocks, compare, corrected_blocks, save_docx, libreoffice_convert

RED='#850D1C'; DARK='#20232A'; BG='#F3F4F6'; GREEN='#D5F3DC'

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
        super().__init__(); self.pdf=None; self.page=0; self.zoom=1.15; self.marks=[]; self.title=title
        lay=QVBoxLayout(self); lay.setContentsMargins(8,8,8,8)
        bar=QHBoxLayout(); self.heading=QLabel(title); self.heading.setStyleSheet('font-weight:700')
        bar.addWidget(self.heading); bar.addStretch()
        self.prev=QPushButton('‹');self.next=QPushButton('›');self.counter=QLabel('0 / 0')
        self.minus=QPushButton('−');self.plus=QPushButton('+')
        for w in (self.prev,self.counter,self.next,self.minus,self.plus):bar.addWidget(w)
        lay.addLayout(bar)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(False);self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        self.canvas=QLabel('Pilih dokumen lalu klik Bandingkan');self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet('background:white; color:#6B7280;');self.canvas.setMinimumSize(420,560)
        self.scroll.setWidget(self.canvas);lay.addWidget(self.scroll,1)
        self.prev.clicked.connect(lambda:self.goto(self.page-1));self.next.clicked.connect(lambda:self.goto(self.page+1))
        self.plus.clicked.connect(lambda:self.set_zoom(self.zoom+.15));self.minus.clicked.connect(lambda:self.set_zoom(self.zoom-.15))
    def set_zoom(self,z):self.zoom=max(.6,min(2.3,z));self.render()
    def load(self,path,marks):
        if self.pdf:self.pdf.close()
        self.pdf=fitz.open(path);self.marks=marks;self.page=0;self.render()
    def goto(self,page):
        if self.pdf and 0<=page<len(self.pdf):self.page=page;self.render()
    def render(self):
        if not self.pdf:return
        p=self.pdf[self.page];pix=p.get_pixmap(matrix=fitz.Matrix(self.zoom,self.zoom),alpha=False)
        img=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
        painter=QPainter(img);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for m in self.marks:
            if m['page']!=self.page:continue
            rect=m['rect']*fitz.Matrix(self.zoom,self.zoom)
            col=QColor('#F6B6BF' if m['side']=='exam' else GREEN)
            painter.fillRect(int(rect.x0),int(rect.y0),max(3,int(rect.width)),max(3,int(rect.height)),col)
            painter.setPen(QPen(QColor(RED),2));painter.drawRect(int(rect.x0),int(rect.y0),max(3,int(rect.width)),max(3,int(rect.height)))
            x=min(img.width()-24,max(4,int(rect.x1)+3));y=max(22,int(rect.y0))
            painter.setBrush(QColor(RED));painter.setPen(Qt.PenStyle.NoPen);painter.drawEllipse(x,y-18,22,22)
            painter.setPen(QColor('white'));painter.setFont(QFont('Arial',9,QFont.Weight.Bold));painter.drawText(x,y-18,22,22,Qt.AlignmentFlag.AlignCenter,str(m['id']))
        painter.end();self.canvas.setPixmap(QPixmap.fromImage(img));self.canvas.resize(img.size())
        self.counter.setText(f'{self.page+1} / {len(self.pdf)}')


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
        super().__init__();self.setWindowTitle('DocMatch v0.2 — Visual Audit (Offline)');self.resize(1550,920)
        self.tmp=tempfile.TemporaryDirectory(prefix='docmatch_v02_');self.work=Path(self.tmp.name)
        self.ref_path=None;self.exam_path=None;self.reference=[];self.examined=[];self.diffs=[];self.ref_pages={};self.exam_pages={};self.checks=[]
        root=QWidget();self.setCentralWidget(root);main=QVBoxLayout(root);main.setContentsMargins(14,12,14,12)
        header=QHBoxLayout();brand=QLabel('▣  DocMatch');brand.setStyleSheet(f'font-size:24px;font-weight:800;color:{RED}')
        header.addWidget(brand);header.addWidget(QLabel('Pembanding & Koreksi Dokumen  •  100% Offline'));header.addStretch();main.addLayout(header)
        toolbar=QHBoxLayout();self.ref_btn=QPushButton('Pilih Dokumen Rujukan');self.exam_btn=QPushButton('Pilih Dokumen Diperiksa')
        self.run_btn=QPushButton('⌕  Bandingkan Dokumen');self.run_btn.setObjectName('primary')
        self.ref_btn.clicked.connect(lambda:self.pick('ref'));self.exam_btn.clicked.connect(lambda:self.pick('exam'));self.run_btn.clicked.connect(self.run)
        for b in (self.ref_btn,self.exam_btn,self.run_btn):toolbar.addWidget(b)
        main.addLayout(toolbar)
        split=QSplitter(Qt.Orientation.Horizontal);self.ref_view=Paper('DOKUMEN RUJUKAN');self.exam_view=Paper('DOKUMEN DIPERIKSA')
        split.addWidget(self.ref_view);split.addWidget(self.exam_view)
        side=QWidget();side.setMinimumWidth(320);side.setMaximumWidth(440);s=QVBoxLayout(side)
        heading=QLabel('Daftar Ketidaksesuaian');heading.setStyleSheet('font-size:17px;font-weight:700');s.addWidget(heading)
        self.filter=QComboBox();self.filter.addItems(['Semua','Perubahan','Hilang','Berlebih']);self.filter.currentTextChanged.connect(self.populate);s.addWidget(self.filter)
        self.list=QListWidget();self.list.currentRowChanged.connect(self.navigate);s.addWidget(self.list,1)
        self.detail=QLabel('Pilih ketidaksesuaian untuk melihat detail.');self.detail.setWordWrap(True);self.detail.setMinimumHeight(90);s.addWidget(self.detail)
        self.apply_btn=QPushButton('Ekspor Koreksi Terpilih (DOCX)');self.apply_btn.setObjectName('primary');self.apply_btn.clicked.connect(self.export_docx)
        self.pdf_btn=QPushButton('Ekspor Koreksi (PDF)');self.pdf_btn.clicked.connect(self.export_pdf)
        self.report_btn=QPushButton('Ekspor Laporan (JSON)');self.report_btn.clicked.connect(self.export_report)
        for b in (self.apply_btn,self.pdf_btn,self.report_btn):s.addWidget(b)
        split.addWidget(side);split.setSizes([530,530,380]);main.addWidget(split,1)
        self.status=QLabel('Siap. Pilih dua dokumen DOCX, PDF, atau DOC. Pratinjau DOCX/DOC membutuhkan LibreOffice lokal.')
        main.addWidget(self.status)
        self.setStyleSheet(f'''QMainWindow,QWidget{{background:{BG};color:{DARK};font-family:Segoe UI,Arial;font-size:12px}}
          QPushButton{{background:white;border:1px solid #D8DADF;border-radius:7px;padding:10px 13px}}
          QPushButton:hover{{border-color:{RED}}} QPushButton#primary{{background:{RED};color:white;border:0;font-weight:700}}
          QScrollArea{{border:1px solid #E0E2E6;background:#E8EAEE}} QListWidget,QComboBox{{background:white;border:1px solid #D8DADF;border-radius:6px;padding:7px}}
          QListWidget::item{{padding:8px;border-bottom:1px solid #EEEEEE}} QListWidget::item:selected{{background:#F6DCE0;color:#242424}}''')
    def pick(self,side):
        name,_=QFileDialog.getOpenFileName(self,'Pilih dokumen','','Dokumen (*.docx *.pdf *.doc)')
        if not name:return
        p=Path(name)
        if side=='ref':self.ref_path=p;self.ref_btn.setText('Rujukan: '+p.name)
        else:self.exam_path=p;self.exam_btn.setText('Diperiksa: '+p.name)
    def run(self):
        if not self.ref_path or not self.exam_path:QMessageBox.warning(self,'Berkas belum lengkap','Pilih kedua dokumen.');return
        try:
            self.reference,_=read_blocks(self.ref_path,self.work);self.examined,_=read_blocks(self.exam_path,self.work)
            self.diffs=compare(self.reference,self.examined)
            # Separate directories avoid collisions when both inputs share a filename.
            a=self.work/'ref';b=self.work/'exam';a.mkdir(exist_ok=True);b.mkdir(exist_ok=True)
            refpdf=make_preview(self.ref_path,a);exampdf=make_preview(self.exam_path,b)
            rm,self.ref_pages,rmiss=locate(refpdf,self.diffs,'ref');em,self.exam_pages,emiss=locate(exampdf,self.diffs,'exam')
            self.ref_view.load(refpdf,rm);self.exam_view.load(exampdf,em);self.populate()
            self.status.setText(f'{len(self.diffs)} perbedaan blok · Anotasi ditemukan: rujukan {len(rm)}, diperiksa {len(em)} · Lokasi tidak ditemukan: {len(set(rmiss+emiss))}.')
        except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def populate(self,*args):
        self.list.clear();self.visible=[]
        for i,d in enumerate(self.diffs):
            if self.filter.currentText() not in ('Semua',d.kind):continue
            self.visible.append(i);label=(d.examined_text or d.reference_text).replace('\n',' ')[:95]
            item=QListWidgetItem(f'#{i+1}  {d.kind}\n{label}');item.setData(Qt.ItemDataRole.UserRole,i)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if d.apply else Qt.CheckState.Unchecked);self.list.addItem(item)
        try:self.list.itemChanged.disconnect(self.changed)
        except (RuntimeError,TypeError):pass
        self.list.itemChanged.connect(self.changed)
    def changed(self,item):self.diffs[item.data(Qt.ItemDataRole.UserRole)].apply=item.checkState()==Qt.CheckState.Checked
    def navigate(self,row):
        if row<0 or row>=len(self.visible):return
        i=self.visible[row];d=self.diffs[i];n=i+1
        if n in self.ref_pages:self.ref_view.goto(self.ref_pages[n])
        if n in self.exam_pages:self.exam_view.goto(self.exam_pages[n])
        self.detail.setText(f'#{n} · {d.kind}\n\nRujukan: {d.reference_text[:240] or "(tidak ada)"}\n\nDiperiksa: {d.examined_text[:240] or "(hilang)"}\n\nCatatan: penanda halaman adalah perkiraan berbasis pencarian teks.')
    def ensure(self):
        if not self.diffs:QMessageBox.warning(self,'Belum dibandingkan','Jalankan perbandingan terlebih dahulu.');return False
        return True
    def export_docx(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan DOCX','docmatch_hasil.docx','DOCX (*.docx)')
        if name:
            try:save_docx(corrected_blocks(self.examined,self.diffs),Path(name));QMessageBox.information(self,'Selesai','DOCX berhasil disimpan. Tata letak asli belum dipertahankan.')
            except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def export_pdf(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan PDF','docmatch_hasil.pdf','PDF (*.pdf)')
        if name:
            try:
                src=self.work/'corrected.docx';save_docx(corrected_blocks(self.examined,self.diffs),src)
                pdf=libreoffice_convert(src,'pdf',self.work);shutil.copyfile(pdf,name)
                QMessageBox.information(self,'Selesai','PDF berhasil disimpan.')
            except Exception as e:QMessageBox.critical(self,'Gagal',str(e))
    def export_report(self):
        if not self.ensure():return
        name,_=QFileDialog.getSaveFileName(self,'Simpan laporan','docmatch_laporan.json','JSON (*.json)')
        if name:
            report={'reference':str(self.ref_path),'examined':str(self.exam_path),'differences':[
                {**asdict(d),'number':i+1,'reference_page':self.ref_pages.get(i+1, -1)+1 if i+1 in self.ref_pages else None,
                 'examined_page':self.exam_pages.get(i+1,-1)+1 if i+1 in self.exam_pages else None} for i,d in enumerate(self.diffs)]}
            Path(name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            QMessageBox.information(self,'Selesai','Laporan disimpan.')

if __name__=='__main__':
    app=QApplication(sys.argv);w=Window();w.show();sys.exit(app.exec())
