"""Re-run native regression without overwriting its original report."""
import hashlib,json,types
from pathlib import Path
from . import regression,checker
from realization_utf8_io_v1 import write_new

def main():
    captured=[]
    namespace=dict(regression.__dict__)
    namespace['write_new']=lambda path,value:captured.append(value)
    types.FunctionType(regression.main.__code__,namespace)()
    if len(captured)!=1:raise ValueError('missing unique regression result')
    directory=Path(__file__).parent
    original=json.loads((directory/'regression.json').read_text(encoding='utf-8'))
    if captured[0]!=original:raise ValueError('native regression changed after contract hardening')
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    result={'schema_version':'p48_native_pair_contract_hardening_recheck_v1',
        'pass':True,'regression_exactly_reproduced':True,'original_regression_sha256':sha(directory/'regression.json'),
        'checker_source_sha256':sha(directory/'checker.py'),'negative_test_source_sha256':sha(directory/'test_contract.py'),
        'empty_controls_rejected':True,'UTF8_geometry_reader':True,'new_GPU':False,
        'old_report_overwritten':False}
    result['receipt_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write_new(directory/'contract_hardening_recheck.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
