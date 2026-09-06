import ast,unittest
from pathlib import Path
from kinematics_cpu import verify_recorded_fk

class ReplayTests(unittest.TestCase):
    def test_all_recorded_FK_and_mesh_aliases(self):self.assertTrue(verify_recorded_fk()['pass'])
    def test_no_scene_or_action_construction(self):
        t=ast.parse(Path(__file__).with_name('replay.py').read_text())
        calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        self.assertFalse(calls&{'Scene','Engine','create_scene','create_actor_builder','opened_scene','take_dense_action','plan_single','plan_path','solve_single','step'})
    def test_original_locked_copy_bug_cpu(self):
        import torch
        from curobo.types.base import TensorDeviceType
        from curobo.types.state import JointState
        args=TensorDeviceType(device=torch.device('cpu'))
        a=JointState(position=torch.tensor([.04,.04]),joint_names=['fl_joint7','fl_joint8'],tensor_args=args)
        b=JointState(position=torch.tensor([.045,.044]),joint_names=['fl_joint7','fl_joint8'],tensor_args=args)
        returned=a.copy_(b)
        self.assertFalse(torch.equal(a.position,b.position));self.assertTrue(torch.equal(returned.position,b.position))
        a.position.copy_(b.position);self.assertTrue(torch.equal(a.position,b.position))

if __name__=='__main__':unittest.main(verbosity=2)
