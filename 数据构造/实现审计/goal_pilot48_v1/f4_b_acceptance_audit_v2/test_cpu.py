"""Synthetic dependency-return fixtures only; original helper asserts on failure."""
from pathlib import Path
import unittest
from unittest.mock import patch
from . import audit

class Tests(unittest.TestCase):
    def case(self,current,*,components_match=True):
        row={'status':'branch_locally_verified','checks':{'raw':True},'current_storage_audit':current,'current_RGB_persisted':current is not None}
        reference={'model_visible_components':{'head_rgb_sha256':'sealed'}}
        metadata={'current':{'model_visible_components':reference['model_visible_components'] if components_match else {'head_rgb_sha256':'different'}}}
        with patch.object(audit.old,'branch',return_value=row),patch.object(audit.old,'read',return_value=metadata):
            return audit.branch(Path('/nfs_share/lijunhui/Robotwin2/tmp/CPU_root'),'F4-ABC',reference,Path('/nfs_share/lijunhui/Robotwin2/tmp/CPU_current'))
    def test_false_return_must_not_mean_verified_presence(self):
        row=self.case({'pass':False,'unique_articulation_dofs':38,'model_visible_robot_state_dimension':76})
        self.assertFalse(row['current_storage_verified']);self.assertEqual(row['status'],'branch_check_failed')
    def test_wrong_layout_or_missing_current_never_passes(self):
        for value in (None,{'pass':True,'unique_articulation_dofs':76,'model_visible_robot_state_dimension':152},{'pass':True,'unique_articulation_dofs':38,'model_visible_robot_state_dimension':75}):
            self.assertFalse(self.case(value)['current_storage_verified'])
    def test_changed_sealed_RGB_components_rejected(self):
        self.assertFalse(self.case({'pass':True,'unique_articulation_dofs':38,'model_visible_robot_state_dimension':76},components_match=False)['current_storage_verified'])
    def test_explicit_true_exact_layout_and_components_pass(self):
        self.assertTrue(self.case({'pass':True,'unique_articulation_dofs':38,'model_visible_robot_state_dimension':76})['current_storage_verified'])
    def test_direct_run_never_uses_presence_as_eligibility(self):
        fake={'rows':[{'current_RGB_persisted':True,'current_storage_verified':False} for _ in range(3)],'eligible_candidate_cells':3,'eligibility_recommendation':'old_fixture_eligible'}
        with patch.object(audit,'bound_function',return_value=lambda *a,**kw:fake):
            report=audit.run(Path('/nfs_share/lijunhui/Robotwin2/tmp/CPU_root'),current_directory=Path('/nfs_share/lijunhui/Robotwin2/tmp/CPU_current'))
        self.assertEqual(report['eligible_candidate_cells'],0);self.assertEqual(report['eligibility_recommendation'],'pending_not_registered')

if __name__=='__main__':unittest.main(verbosity=2)
