"""Penjalan tes tanpa pytest: python tests/run_tests.py  (pytest tetap didukung)."""
import importlib, sys, types
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
try:
    import pytest  # noqa: F401
    raise SystemExit(pytest.main(['-q', str(ROOT)]))
except ImportError:
    pass


class Skip(Exception):
    pass


class _Monkey:
    """monkeypatch minimal (setitem/setattr) untuk menjalankan tes tanpa pytest."""
    def __init__(self):
        self._undo = []

    def setitem(self, mapping, key, value):
        self._undo.append((mapping, key, mapping.get(key, _Monkey)))
        mapping[key] = value

    def setattr(self, obj, name, value):
        self._undo.append((obj, name, getattr(obj, name, _Monkey)))
        setattr(obj, name, value)

    def undo(self):
        for target, key, old in reversed(self._undo):
            if isinstance(target, dict):
                target.pop(key, None) if old is _Monkey else target.__setitem__(key, old)
            else:
                setattr(target, key, old)


shim = types.ModuleType('pytest')
def importorskip(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        raise Skip(name)
def skip(msg=''):
    raise Skip(msg)
class mark:
    @staticmethod
    def parametrize(names, values):
        def deco(fn):
            # dekorator bertumpuk: gabungkan sebagai hasil kali kartesian
            columns = names.split(',')
            rows = [v if isinstance(v, tuple) else (v,) for v in (list(values.items()) if isinstance(values, dict) else values)]
            old = getattr(fn, '_params', None)
            if old:
                ocols, orows = old
                rows = [o + n for o in orows for n in rows]
                columns = ocols + columns
            fn._params = (columns, rows)
            return fn
        return deco
shim.importorskip, shim.skip, shim.mark = importorskip, skip, mark
sys.modules['pytest'] = shim
passed = failed = skipped = 0
_only = [a for a in sys.argv[1:] if not a.startswith('-')]
for path in sorted(ROOT.glob('test_*.py')):
    if _only and path.stem not in _only:
        continue
    try:
        mod = importlib.import_module(path.stem)
    except (Skip, ImportError) as exc:
        print('SKIP', path.name, exc); skipped += 1; continue
    for name in dir(mod):
        fn = getattr(mod, name)
        if not (name.startswith('test_') and callable(fn)):
            continue
        params = getattr(fn, '_params', None)
        cases = [v if isinstance(v, tuple) else (v,) for v in params[1]] if params else [()]
        import inspect
        names_order = params[0] if params else []
        fixtures = [p for p in inspect.signature(fn).parameters if p not in names_order]
        for case in cases:
            label = f'{path.stem}.{name}{case if case else ""}'
            if any(f not in ('monkeypatch', 'tmp_path') for f in fixtures):
                skipped += 1; print('SKIP', label, 'butuh fixture pytest:', fixtures); continue
            mp = _Monkey()
            import tempfile
            from pathlib import Path as _P
            extra = [mp if f == 'monkeypatch' else _P(tempfile.mkdtemp()) for f in fixtures]
            try:
                kwargs = dict(zip(names_order, case))
                kwargs.update({f: e for f, e in zip(fixtures, extra)})
                fn(**kwargs); passed += 1; print('PASS', label)
            except Skip as exc:
                skipped += 1; print('SKIP', label, exc)
            except Exception as exc:
                failed += 1; print('FAIL', label, '->', str(exc)[:300])
            finally:
                mp.undo()
print(f'\nlulus {passed}, gagal {failed}, dilewati {skipped}')
raise SystemExit(1 if failed else 0)
