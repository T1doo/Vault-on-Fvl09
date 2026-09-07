import unittest
from .controller import after_micro_sequence
def passed():return {'pass':True,'full_world_restoration_checks':{k:{'valid':True} for k in ('motion_gen','motion_gen_batch')}}
class Tests(unittest.TestCase):
    def test_micro_fail_cannot_restore_lift_or_V(self):
        def forbidden(*a):raise AssertionError('continuation after failed micro')
        r=after_micro_sequence({'pass':False},*[forbidden]*5);self.assertFalse(r['pass'])
    def test_exact_order(self):
        calls=[]
        def f(name):return lambda *a:calls.append(name)
        after_micro_sequence(passed(),*[f(x) for x in ('receipt','full_world','15mm','40mm','preV_then_V')])
        self.assertEqual(calls,['full_world','receipt','15mm','40mm','preV_then_V'])
    def test_each_early_error_stops_before_V(self):
        for failure in ('receipt','full_world','15mm','40mm'):
            calls=[]
            def make(n):
                def cb(*a):
                    calls.append(n)
                    if n==failure:raise RuntimeError(n)
                return cb
            with self.assertRaises(RuntimeError):after_micro_sequence(passed(),*[make(n) for n in ('receipt','full_world','15mm','40mm','V')])
            self.assertNotIn('V',calls)
    def test_empty_restoration_cannot_continue(self):
        def bad(*a):raise AssertionError('called past failed restoration')
        with self.assertRaises(ValueError):after_micro_sequence({'pass':True,'full_world_restoration_checks':{}},*[bad]*5)
if __name__=='__main__':unittest.main()
