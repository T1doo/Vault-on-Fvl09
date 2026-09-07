"""Directionality and saved V1 failure regression, no new physical evidence."""
import copy,json,unittest
from pathlib import Path
from .certificate import validate,seal,SCHEMA
from .test_certificate import fixture,reseal
from goal_pilot48_v1.f3_tangent_escape_v1.certificate import validate as validate_v1
class Tests(unittest.TestCase):
    def test_positive108um_allowed_negative108um_rejected(self):
        for gap,passed in ((.0001088205,True),(-.0001088205,False)):
            c=fixture();c['native_gap_per_hold_frame_m']=[gap]*250;self.assertEqual(validate(reseal(c)),passed)
    def test_epsilon_cannot_be_increased_or_positive_cap_reintroduced(self):
        for key,value in [('native_lower_bound_epsilon_m',.00012),('positive_gap_upper_bound_m',.00012),('model_eligibility_revision',1)]:
            c=fixture();c[key]=value;self.assertFalse(validate(reseal(c)))
    def test_positive_gap_does_not_authorize_full_valid_or_empty_pair(self):
        c=fixture();c['native_gap_per_hold_frame_m']=[.001]*250
        c['full_model_checks']={k:{'valid':True,'status':None} for k in ('motion_gen','motion_gen_batch')};self.assertFalse(validate(reseal(c)))
        c=fixture();c['overlap_pairs']=[];c['old_supported_witness']['pairs']=[];self.assertFalse(validate(reseal(c)))
    def test_inconsistent_old_pair_summary_rejected(self):
        c=fixture();c['old_supported_witness']['only_attached_bottle_support_pairs_overlap']=False;self.assertFalse(validate(reseal(c)))
    def test_saved_V1_failure_preserved_and_V2_counterfactual_only(self):
        p=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_tangent_micro_001/tangent_certificate_candidate.json');before=p.read_bytes();original=json.loads(before)
        self.assertFalse(validate_v1(original));self.assertFalse(validate(original))
        # CPU counterfactual schema review only: never publish this as a fresh certificate.
        c=copy.deepcopy(original);c.pop('certificate_sha256');c.update(schema_version=SCHEMA,model_eligibility_revision=2,native_lower_bound_epsilon_m=.0001,positive_gap_upper_bound_m=None)
        self.assertTrue(validate(seal(c)));self.assertEqual(p.read_bytes(),before)
if __name__=='__main__':unittest.main()
