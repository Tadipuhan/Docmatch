"""Offline OCR fallback for unreadable GSL PDF fields. No network requests."""
from __future__ import annotations
import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pymupdf as fitz

class OCRError(RuntimeError):
    pass

def tesseract_path():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    exe = "tesseract.exe" if os.name == "nt" else "tesseract"
    candidates = (base / "tesseract" / exe, Path(sys.executable).resolve().parent / "tesseract" / exe, Path(__file__).resolve().parent / "tesseract" / exe)
    for path in candidates:
        if path.is_file(): return str(path)
    found = shutil.which("tesseract")
    if found: return found
    raise OCRError("Tesseract OCR offline tidak ditemukan. Pada build portable, salin folder tesseract beserta tessdata ke paket aplikasi.")

class PageOCR:
    def __init__(self, doc, dpi=300):
        self.doc=doc
        self.dpi=dpi
        self.cache={}

    def words(self, page_no):
        if page_no in self.cache: return self.cache[page_no]
        page=self.doc[page_no]
        pix=page.get_pixmap(matrix=fitz.Matrix(self.dpi/72,self.dpi/72),alpha=False)
        image=pix.tobytes("png")
        exe=tesseract_path()
        env=os.environ.copy()
        base=Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        tessdata=Path(exe).resolve().parent/"tessdata"
        if tessdata.is_dir(): env["TESSDATA_PREFIX"]=str(tessdata)
        try:
            proc=subprocess.run([exe,"stdin","stdout","-l","eng","--psm","11","tsv"],
                input=image,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=120,env=env,check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OCRError("Tesseract gagal dijalankan: "+str(exc)) from exc
        if proc.returncode:
            raise OCRError("Tesseract gagal: "+proc.stderr.decode("utf-8",errors="replace")[-400:])
        output=[]
        scale=72/self.dpi
        for r in csv.DictReader(io.StringIO(proc.stdout.decode("utf-8-sig",errors="replace")),delimiter="\t"):
            token=r.get("text","").strip()
            if not token: continue
            try:
                confidence=float(r.get("conf","-1"))
                x,y,w,h=(int(r[k]) for k in ("left","top","width","height"))
            except (ValueError,TypeError,KeyError): continue
            if confidence < 35 or w <= 0 or h <= 0: continue
            rect=fitz.Rect(x*scale,y*scale,(x+w)*scale,(y+h)*scale)
            output.append({"word":token,"rect":rect,"page":page_no,"confidence":confidence})
        self.cache[page_no]=output
        return output

def recover_field(doc, regions, rect_function, engine):
    words=[]
    for page_no,*bounds in regions:
        if page_no>=len(doc): continue
        clip=rect_function(doc[page_no],bounds)
        for word in engine.words(page_no):
            if clip.contains((word["rect"].tl+word["rect"].br)*.5):
                words.append(word)
    if not words:
        return {"text":"","words":[],"valid":False,"reason":"OCR tidak menemukan teks pada kotak ini"}
    mean=sum(w["confidence"] for w in words)/len(words)
    # OCR confidence is only an estimate, not proof of correct numbers.
    if mean < 55:
        return {"text":" ".join(w["word"] for w in words),"words":words,"valid":False,
                "reason":f"Rata-rata confidence OCR {mean:.0f}, perlu verifikasi"}
    return {"text":" ".join(w["word"] for w in words),"words":words,"valid":True,
            "source":"OCR","confidence":mean}


def ocr_status():
    """Return explicit diagnostics for offline OCR availability."""
    try:
        exe=tesseract_path()
        base=Path(exe).resolve().parent
        data=base/'tessdata'/'eng.traineddata'
        if not data.is_file():
            # System installations may use a different tessdata directory.
            check=subprocess.run([exe,'--list-langs'],capture_output=True,text=True,timeout=15)
            if check.returncode or 'eng' not in check.stdout.split():
                return False, 'Tesseract ditemukan, tetapi bahasa eng tidak tersedia: '+exe
        probe=subprocess.run([exe,'--version'],capture_output=True,text=True,timeout=15)
        if probe.returncode: return False, 'Tesseract gagal dijalankan: '+probe.stderr[-250:]
        return True, 'Tesseract OCR siap: '+exe
    except (OCRError,OSError,subprocess.TimeoutExpired) as exc:
        return False, str(exc)
