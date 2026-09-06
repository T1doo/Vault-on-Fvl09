import ast,unittest
from pathlib import Path
from ik_config import validate_profiles,profile_config

class Tests(unittest.TestCase):
    def test_profiles(self):self.assertTrue(validate_profiles())
    def test_seed_tolerance_budget_fixed(self):
        configs=[profile_config(x)['kwargs'] for x in ('K0','K1','K2')]
        for key in ('num_seeds','position_threshold','rotation_threshold','grad_iters','seed'):
            self.assertEqual(len({c[key] for c in configs}),1)
    def test_no_physical_api(self):
        tree=ast.parse((Path(__file__).parent/'execute.py').read_text(encoding='utf-8'))
        forbidden={'step','move','set_drive_target','set_left_arm_jointState','close_gripper','execute_controls'}
        self.assertFalse([n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute) and n.attr in forbidden])
    def test_yaw_preserves_center(self):
        import numpy as np
        from execute import corrected_contract,yaw_targets,P
        import json,transforms3d as t3d
        c,_=corrected_contract();data=json.loads((P/'assets/objects/071_can/model_data0.json').read_text());center=np.array(data['center'])*.05
        for angle in (90,-90,180):
            t=yaw_targets(c,angle);pose=np.array(t['actor_pose']);actual=pose[:3]+t3d.quaternions.quat2mat(pose[3:])@center
            np.testing.assert_allclose(actual[:2],c['beside_candidate_xy_m'],atol=1e-12)
            np.testing.assert_allclose(np.array(t['U'])[:3]-np.array(t['D'])[:3],[0,0,.08],atol=1e-12)

if __name__=='__main__':unittest.main()
