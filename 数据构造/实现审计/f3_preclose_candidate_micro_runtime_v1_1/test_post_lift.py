import copy,unittest
from post_lift_audit import audit_micro_lift_trace
from controlled_multi_future.f3_physical_contact_signal_v8 import CONTACT_PAIR_SCHEMA_VERSION,canonical_json_sha256

def contact(a,b):
    ids=[]
    for i,body in enumerate((a,b)):
        x={'available':True,'body_name':body,'collision_shape_index':i,'collision_shape_type':'synthetic','collision_groups':[1,1,0,i]}
        x['identity_sha256']=canonical_json_sha256(x);ids.append(x)
    return {'contact_pair_schema_version':CONTACT_PAIR_SCHEMA_VERSION,'body_a':a,'body_b':b,'point_count':1,
        'impulse_norm_sum':.1,'impulse_available':True,'shape_identity_available':True,'shape_identities':ids,
        'point_evidence':[{'point_index':0,'impulse_norm':.1,'impulse_available':True,'signed_separation_m':-.001,
            'signed_separation_available':True,'shape_identity_available':True,'shape_identity_sha256':[x['identity_sha256'] for x in ids]}]}

class PostLiftTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for i in range(53):
            z=.025*min(i,2)/2
            rows.append({'step_index':i,'timestamp':i*.004,'eef':[0,0,1+z,1,0,0,0],
                'actor_pose':[0,0,.8+z,1,0,0,0],'contact_pairs':[contact('fl_link7','bottle')]})
        receipt={'start_trace_row':0,'end_trace_row':2,'segment_id':'f3_micro_lift25','planner_status':'Success',
            'tracking_position_error_m':0.,'tracking_orientation_error_rad':0.}
        return rows,receipt
    def audit(self,rows,receipt):return audit_micro_lift_trace(rows,baseline_row=0,lift_receipt=receipt,arm='left',selected_links=['fl_link7','fl_link8'],bottle_name='bottle',support_names=['table','pad'])
    def test_complete_valid_micro_lift(self):
        rows,r=self.fixture();a=self.audit(rows,r);self.assertTrue(a['pass'],a);self.assertEqual(a['confirmation_rows'],50)
    def test_only_last_frame_off_support_rejected(self):
        rows,r=self.fixture()
        for row in rows[3:-1]:row['contact_pairs'].append(contact('bottle','pad'))
        a=self.audit(rows,r);self.assertFalse(a['pass']);self.assertFalse(a['checks']['confirmation_off_support'])
    def test_no_actual_bottle_rise(self):
        rows,r=self.fixture()
        for row in rows:row['actor_pose'][2]=.8;row['eef'][2]=1.
        a=self.audit(rows,r);self.assertFalse(a['pass']);self.assertFalse(a['checks']['actual_rise'])
    def test_transient_slip_then_return(self):
        rows,r=self.fixture();rows[1]['actor_pose'][0]+=.006
        a=self.audit(rows,r);self.assertFalse(a['pass']);self.assertFalse(a['checks']['full_window_transform'])
    def test_confirmation_missing_frame(self):
        rows,r=self.fixture();del rows[20];self.assertFalse(self.audit(rows,r)['pass'])
    def test_duplicate_step_rejected(self):
        rows,r=self.fixture();rows[20]['step_index']=19;self.assertFalse(self.audit(rows,r)['pass'])
    def test_post_lift_self_collision(self):
        rows,r=self.fixture();rows[20]['contact_pairs'].append(contact('fl_link6','fl_link4'))
        a=self.audit(rows,r);self.assertFalse(a['pass']);self.assertFalse(a['checks']['no_forbidden_arm_collisions'])
    def test_post_lift_arm_support_collision(self):
        rows,r=self.fixture();rows[20]['contact_pairs'].append(contact('fl_link6','table'));self.assertFalse(self.audit(rows,r)['pass'])
    def test_incomplete_contact(self):
        rows,r=self.fixture();rows[20]['contact_pairs'][0]['shape_identity_available']=False;self.assertFalse(self.audit(rows,r)['pass'])
    def test_missing_contact_field(self):
        rows,r=self.fixture();del rows[20]['contact_pairs'];self.assertFalse(self.audit(rows,r)['pass'])
    def test_missing_lift_receipt_field(self):
        rows,r=self.fixture();del r['planner_status'];self.assertFalse(self.audit(rows,r)['pass'])
    def test_contact_lost_during_lift(self):
        rows,r=self.fixture();rows[1]['contact_pairs']=[];self.assertFalse(self.audit(rows,r)['pass'])

if __name__=='__main__':unittest.main()
