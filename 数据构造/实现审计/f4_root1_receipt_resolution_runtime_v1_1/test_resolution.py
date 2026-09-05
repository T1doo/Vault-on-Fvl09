import ast,copy,unittest
from pathlib import Path
from resolution import derive,authorization,load_original_branch,sha,A,FIELD

class ResolutionTests(unittest.TestCase):
    def pair(self):
        old={'status':'accepted','executed_prefix':{FIELD:2851,'canonical_prefix_end_step':2851}}
        new=copy.deepcopy(old);new['executed_prefix'][FIELD]=2926
        return old,new
    def test_single_field_and_original_immutable(self):
        old,new=self.pair();before=copy.deepcopy(old);self.assertEqual(derive(old,new,2926),new);self.assertEqual(old,before)
    def test_wrong_divergence(self):
        old,new=self.pair()
        with self.assertRaises(ValueError):derive(old,new,2927)
    def test_bool_is_not_step(self):
        old,new=self.pair()
        with self.assertRaises(ValueError):derive(old,new,True)
    def test_extra_field_rejected(self):
        old,new=self.pair();new['status']='failed'
        with self.assertRaises(ValueError):derive(old,new,2926)
    def test_P_change_rejected(self):
        old,new=self.pair();new['executed_prefix']['canonical_prefix_end_step']=2926
        with self.assertRaises(ValueError):derive(old,new,2926)
    def test_bad_original_hash_rejected(self):
        with self.assertRaises(ValueError):load_original_branch('F4-ABC','0'*64)
    def test_explicit_disk_reader_imports(self):
        from finalizer import _read_mapping
        from resolution import AUTH
        self.assertIn("decision",_read_mapping(AUTH,"approval"))
    def test_exact_authorization(self):
        _,f=authorization();self.assertEqual(f['maximum_gpu_executions'],0);self.assertEqual(f['maximum_existing_roots_adopted'],1)
    def test_finalizer_only_explicit_reader_change(self):
        source=(A/'f4_development_root_runtime_v2_2/job_runner.py').read_text()
        revised=(Path(__file__).parent/'finalizer.py').read_text()
        old={n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        for n in ast.parse(revised).body:
            if not isinstance(n,ast.FunctionDef):continue
            expected=old[n.name].replace('*, output: Path) -> dict[str, Any]:','*, output: Path, branch_loader) -> dict[str, Any]:')
            expected=expected.replace('_read_mapping(branch_path, f"{program_id} branch receipt")','branch_loader(branch_path, program_id)')
            self.assertEqual(ast.get_source_segment(revised,n),expected)
        self.assertNotIn('unittest.mock',revised)

if __name__=='__main__':unittest.main()
