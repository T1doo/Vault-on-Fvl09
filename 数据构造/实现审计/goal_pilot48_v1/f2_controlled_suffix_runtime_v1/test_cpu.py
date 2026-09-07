import json,unittest
from pathlib import Path
import numpy as np
from .interfaces import execute_inside,execute_on,validate_partition_shapes

class Backend:
    def __init__(self,support=True,safety=True):self.log=[];self.support=support;self.safety=safety;self.solver_query_count=0
    def execute_carried_segment(self,i):self.log.append(('carry',i))
    def execute_empty_hand_segment(self,i):self.log.append(('empty',i))
    def wait_and_record(self,n):self.log.append(('wait',n))
    def original_controlled_support_gate(self):return {'pass':self.support}
    def original_release_safety_gate_v10(self):return {'pass':self.safety}
    def open_gripper(self,target):self.log.append(('open',target))
    def begin_final_settle_window(self):self.log.append(('settle_start',))
    def install_actual_released_can_open_gripper_fullworld(self):self.log.append(('released_model',));return {'pass':True}
    def original_final_inside_gate_v10(self):return {'pass':True}
    def scale_support_release_gate(self):return {'pass':self.support}
    def original_on_family_verifier(self):return {'pass':True}

def certificate(relation):return dict(relation=relation,native_support_certified=True,all_robot_and_sidewall_checks_retained=True,blanket_container_disable=False,unchanged_strict_inside_at_support=True)

class Tests(unittest.TestCase):
    def test_inside_controlled_order_and_released_model(self):
        b=Backend();r=execute_inside(b,certificate('inside'));self.assertTrue(r['pass'])
        self.assertEqual([x[1] for x in b.log if x[0]=='open'],[.2,.4,.6,.8,1.])
        self.assertLess(b.log.index(('released_model',)),b.log.index(('empty',3)))
        self.assertEqual(r['planner_queries_during_execution'],0)
    def test_safety_failure_never_full_opens(self):
        b=Backend(safety=False);r=execute_inside(b,certificate('inside'));self.assertFalse(r['pass']);self.assertNotIn(('open',1.),b.log)
    def test_support_failure_never_opens(self):
        b=Backend(support=False);execute_inside(b,certificate('inside'));self.assertFalse(any(x[0]=='open' for x in b.log))
    def test_real_anatomy_blocks_inside_without_any_action(self):
        a=json.loads((Path(__file__).parent/'anatomy.json').read_text(encoding='utf-8'));cert=certificate('inside')
        cert['unchanged_strict_inside_at_support']=a['inside']['strict_inside_at_first_native_contact']['pass_true_cavity_obb'];b=Backend()
        with self.assertRaises(ValueError):execute_inside(b,cert)
        self.assertEqual(b.log,[])
    def test_compound_floor_sidewall_is_not_ignored(self):
        shapes=[dict(name='box__floor_wall',role='box')]
        with self.assertRaises(ValueError):validate_partition_shapes(shapes,['box__floor_wall'],.75,lambda s:np.array([[0,0,.74],[0,0,.85]]))
    def test_on_model_switch_and_no_new_query(self):
        b=Backend();self.assertTrue(execute_on(b,certificate('on'))['pass']);self.assertLess(b.log.index(('released_model',)),b.log.index(('empty',2)))
        b=Backend();b.original_on_family_verifier=lambda:(setattr(b,'solver_query_count',1) or {'pass':True})
        with self.assertRaises(RuntimeError):execute_on(b,certificate('on'))
    def test_independent_cavity_regressions_remain_unadopted(self):
        p=Path(__file__).parent;l=json.loads((p/'cavity_lineage.json').read_text(encoding='utf-8'));r=json.loads((p/'regression.json').read_text(encoding='utf-8'))
        self.assertTrue(l['all_strict_volume_native_intersections_absent']);self.assertTrue(l['native_can_contained_in_verifier_metadata_OBB'])
        self.assertAlmostEqual(l['raw_lower_m'][1]+.005,l['frozen_lower_m'][1],places=14)
        self.assertTrue(r['hypothetical_variants_are_not_adopted_or_execution_authority'])
        self.assertFalse(r['contact_pose_predicate_variants']['native_bounds_hypothetical__frozen_5mm_inset']['pass_true_cavity_obb'])

if __name__=='__main__':unittest.main()
