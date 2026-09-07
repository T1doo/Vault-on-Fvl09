import tempfile,unittest,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from goal_pilot48_v1.f3_runtime_v6 import micro
from .certificate import SinglePlanLease
from .test_certificate import fixture
from .live import restore
class Tests(unittest.TestCase):
    def test_real_restore_hook_expires_lease_and_records_both_states(self):
        lease=SinglePlanLease(fixture());c=lease.certificate;lease.begin_plan(c['scene_id'],c['plan_id'],c['world_sha256'])
        mg=SimpleNamespace(world_coll_checker=SimpleNamespace(calls={'get_sphere_distance':5}))
        planner=SimpleNamespace(motion_gen=mg,motion_gen_batch=mg);scene=SimpleNamespace(robot=SimpleNamespace(left_planner=planner),_cmf_tangent_lease=lease)
        def build(*args):self.assertEqual(lease.state,'expired')
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as d,patch('model_apply.runtime_joint_state',return_value=(['a'],[0.])),patch('model_apply.query_state',return_value=({'valid':True},None)):
            result=restore(scene,Path(d),build)
            r=json.loads((Path(d)/'full_world_restored/restoration.json').read_text(encoding='utf-8'))
            self.assertEqual(r['single_plan_calls'],1);self.assertEqual(r['single_plan_lease_state'],'expired');self.assertEqual(set(result),{'motion_gen','motion_gen_batch'})
            self.assertEqual(r['prior_checker_method_entry_counts_not_GPU_kernel_launch_counts']['motion_gen']['get_sphere_distance'],5)
if __name__=='__main__':unittest.main()
