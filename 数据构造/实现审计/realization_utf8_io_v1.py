"""Locale-independent UTF-8 and exclusive atomic receipt publication."""
import json,os,uuid
from pathlib import Path
W=Path('/nfs_share/lijunhui')

def load_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def write_new(path,value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    path=Path(path).resolve()
    if not path.is_relative_to(W):raise ValueError('outside workspace')
    data=(json.dumps(canonical_jsonable(value),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.parent/(path.name+'.tmp.'+uuid.uuid4().hex)
    try:
        with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.link(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def cpu_test():
    import locale,tempfile
    original=locale.setlocale(locale.LC_CTYPE)
    try:
        locale.setlocale(locale.LC_CTYPE,'C')
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='utf8_receipt_cpu_') as tmp:
            p=Path(tmp)/'receipt.json';value={'source_directory':'数据构造/代码审阅快照','message':'原记录保留'}
            write_new(p,value);assert load_json(p)==value;old=p.read_bytes()
            try:write_new(p,{'overwrite':True})
            except FileExistsError:pass
            else:raise AssertionError('overwrite permitted')
            assert p.read_bytes()==old
            bad=Path(tmp)/'bad.json'
            try:write_new(bad,{'bad':float('nan')})
            except ValueError:pass
            else:raise AssertionError('nonfinite accepted')
            assert not bad.exists();assert not list(Path(tmp).glob('*.tmp.*'))
    finally:locale.setlocale(locale.LC_CTYPE,original)
    return {'forced_C_locale_utf8_roundtrip':True,'exclusive_existing_file_preserved':True,'serialization_failure_no_partial_target':True,'temporary_cleanup':True,'gpu_runs':0}

if __name__=='__main__':print(json.dumps(cpu_test(),sort_keys=True))
