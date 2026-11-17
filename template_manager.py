"""User-editable JSON template aliases; does not change trusted extraction coordinates."""
from __future__ import annotations
from pathlib import Path
import json

DEFAULTS = {'waybill_anl': {}, 'waybill_evergreen': {}, 'waybill_gsl': {}}

def validate_templates(data):
    if not isinstance(data, dict): raise ValueError('Akar template harus objek JSON')
    for profile, fields in data.items():
        if profile not in DEFAULTS or not isinstance(fields, dict):
            raise ValueError('Profil atau format template tidak dikenal: '+str(profile))
        for field, names in fields.items():
            if not isinstance(field,str) or not field.strip() or not isinstance(names,list) or not all(isinstance(x,str) and x.strip() for x in names):
                raise ValueError('Nama field/alias tidak valid pada '+profile)
            if len(names)>30 or any(len(x)>120 for x in names): raise ValueError('Alias template melebihi batas')
    return data

def read_templates(path):
    file = Path(path)
    if not file.exists(): return {k:dict(v) for k,v in DEFAULTS.items()}
    return validate_templates(json.loads(file.read_text(encoding='utf-8')))

def write_templates(path, data):
    # Save with the same atomic-file guarantees but do not inject session metadata.
    import os, tempfile
    dest=Path(path);dest.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(validate_templates(data),ensure_ascii=False,indent=2)
    temp=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=dest.parent,delete=False) as stream:
            temp=Path(stream.name);stream.write(content);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,dest)
    finally:
        if temp is not None and temp.exists():temp.unlink()
    return dest
