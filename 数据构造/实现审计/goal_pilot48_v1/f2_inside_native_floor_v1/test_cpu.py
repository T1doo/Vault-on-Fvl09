import copy,json,unittest
import numpy as np
from .certificate import A,reference_certificate,build_certificate,validate_certificate,digest,matrix,APPROVAL_SHA
from .geometry_verifier import GeometryVerifier
from .contact import shape_identity,verify_floor_contact_row,verify_floor_contact_window
from .physical_gates import final_inside_gate

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=reference_certificate();cls.verifier=GeometryVerifier(cls.c)
        anatomy=json.loads((A/'goal_pilot48_v1/f2_controlled_suffix_runtime_v1/anatomy.json').read_text(encoding='utf-8'))
        cls.pose=anatomy['inside']['first_contact_actor_pose'];cls.box=cls.c['box_shapes'][0]['actor_world_pose']
        cls.contact=cls.verifier.synthetic_contact_geometry(cls.pose,cls.box)

    def geometry(self,p=None,**kwargs):
        return self.verifier.evaluate(self.pose if p is None else p,self.box,binding_sha256=self.c['binding_sha256'],**kwargs)

    def row(self,box_index=None,impulse=0.,separation=0.):
        c=self.c;point=self.contact;ci=point['can_shape_index'];bi=point['box_shape_index'] if box_index is None else box_index
        ids=[shape_identity(c['can_shapes'][ci],ci,c['can_actor_name']),shape_identity(c['box_shapes'][bi],bi,c['box_actor_name'])]
        pair=dict(contact_pair_schema_version='cmf_runtime_contact_pair_v2',body_a=c['can_actor_name'],body_b=c['box_actor_name'],point_count=1,
          impulse_norm_sum=impulse,impulse_available=True,point_impulse_available=[True],shape_identity_available=True,shape_identities=ids,
          point_positions=[point['position_world']],point_normals=[point['normal_world']],point_separations=[separation],point_separation_available=[True],
          point_evidence=[dict(impulse_norm=impulse,impulse_available=True,signed_separation_m=separation,signed_separation_available=True,
            shape_identity_available=True,shape_identity_sha256=[v['identity_sha256'] for v in ids])])
        return dict(role_actor_poses={'main_can':list(self.pose),'box':list(self.box)},actor_pose_frame='world',contact_pairs=[pair],contact_signal_complete=True,
          actor_linear_velocity=[0.,0.,0.],actor_angular_velocity=[0.,0.,0.],CPU_SYNTHETIC_CONTACT_FIXTURE_NOT_A_PHYSICAL_TRAJECTORY=True)

    def test_approved_identity_and_visual_coverage(self):
        self.assertTrue(validate_certificate(self.c));self.assertEqual(self.c['approval_file_sha256'],APPROVAL_SHA)
        self.assertTrue(self.c['native_envelope_contains_visual']);self.assertEqual(len(self.c['floor_shape_indices']),7);self.assertEqual(len(self.c['wall_shape_indices']),8)

    def test_saved_native_boundary_positive_is_geometry_only(self):
        g=self.geometry();self.assertTrue(g['pass']);self.assertFalse(g['physical_support_proven']);self.assertIn(9,g['floor_geometry_candidate_indices'])

    def test_floating_rejected_even_with_fake_pair(self):
        p=np.array(self.pose);p[2]+=.02;self.assertFalse(self.geometry(p)['pass'])
        r=self.row();r['role_actor_poses']['main_can']=p.tolist();self.assertFalse(verify_floor_contact_row(r,self.verifier)['pass'])

    def test_deep_floor_penetration_rejected(self):
        p=np.array(self.pose);p[2]-=.002;g=self.geometry(p)
        self.assertFalse(g['pass']);self.assertTrue(g['floor_penetration_indices'])

    def test_floor_underside_positive_gap_not_mistaken_for_support(self):
        from .certificate import local_vertices
        floor=[s for s in self.c['box_shapes'] if int(s['name'].split('__')[1]) in self.c['floor_shape_indices']]
        lowest=float(local_vertices(floor)[:,1].min()+self.box[2])
        can=local_vertices(self.c['can_shapes']);p=np.array(self.pose)
        p[2]=lowest-self.c['native_boundary_epsilon_m']/2-can[:,2].max()
        g=self.geometry(p);self.assertFalse(g['pass']);self.assertTrue(g['floor_penetration_indices'])

    def test_side_and_top_bounds_exactly_unchanged(self):
        g=self.geometry();B=matrix(self.box);upper=np.asarray(self.c['unchanged_strict_upper_m']);hi=np.asarray(g['local_native_envelope_upper'])
        for axis,key in ((0,'X_sides'),(2,'Z_sides'),(1,'top')):
            p=np.array(self.pose);p[:3]+=B[:3,axis]*(upper[axis]-hi[axis]+.001)
            self.assertFalse(self.geometry(p)['checks'][key])

    def test_wrong_frame_scale_binding_rejected(self):
        with self.assertRaises(ValueError):self.geometry(frame='box_local')
        with self.assertRaises(ValueError):self.geometry(can_scale=[.1]*3)
        with self.assertRaises(ValueError):self.verifier.evaluate(self.pose,self.box,binding_sha256='0'*64)

    def test_wrong_shape_registry_and_compound_wall_certificate_rejected(self):
        c=copy.deepcopy(self.c);c['floor_shape_indices'].append(0);c['receipt_sha256']=digest({k:v for k,v in c.items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):validate_certificate(c)
        can=copy.deepcopy(self.c['can_shapes']);can[0]['shape_scale'][0]*=2
        with self.assertRaises(ValueError):build_certificate(can,self.c['box_shapes'],binding_sha256=self.c['binding_sha256'])

    def test_real_signal_rules_synthetic_fixture_pass_and_false_contact_fail(self):
        self.assertTrue(verify_floor_contact_row(self.row(),self.verifier)['pass'])
        # Positive separation with no impulse is the unchanged original
        # contact-offset-only negative, not physical support.
        self.assertFalse(verify_floor_contact_row(self.row(separation=.001),self.verifier)['pass'])
        r=self.row();r['contact_pairs']=[];self.assertFalse(verify_floor_contact_row(r,self.verifier)['pass'])

    def test_wrong_floor_wall_shape_and_point_frame_rejected(self):
        self.assertFalse(verify_floor_contact_row(self.row(box_index=0),self.verifier)['pass'])
        r=self.row();r['contact_pairs'][0]['point_positions']=[[9,9,9]]
        self.assertFalse(verify_floor_contact_row(r,self.verifier)['pass'])
        r=self.row();r['contact_pairs'][0]['shape_identities'][0]['body_collision_shape_index']=25
        self.assertFalse(verify_floor_contact_row(r,self.verifier)['pass'])

    def test_missing_signal_or_pose_refused(self):
        r=self.row();r['contact_signal_complete']=False;self.assertFalse(verify_floor_contact_row(r,self.verifier)['pass'])
        r=self.row();r['role_actor_poses'].pop('box')
        with self.assertRaises(ValueError):verify_floor_contact_row(r,self.verifier)

    def test_original_frame_counts_and_numeric_final_gates_unchanged(self):
        rows=[self.row() for _ in range(250)]
        self.assertTrue(verify_floor_contact_window(rows[-50:],self.verifier,expected_frames=50)['pass'])
        with self.assertRaises(ValueError):verify_floor_contact_window(rows[-49:],self.verifier,expected_frames=50)
        kw=dict(on_predicate=False,beside_predicate=False,gripper_full_open=True,arm_rest_pass=True)
        result=final_inside_gate(rows,self.verifier,**kw);self.assertTrue(result['pass']);self.assertFalse(result['physical_thresholds_changed'])
        for field,value in (('gripper_full_open',False),('arm_rest_pass',False),('on_predicate',True)):
            self.assertFalse(final_inside_gate(rows,self.verifier,**{**kw,field:value})['pass'])
        rows[-20]['actor_linear_velocity']=[.021,0,0]
        self.assertFalse(final_inside_gate(rows,self.verifier,**kw)['pass'])
        rows[-20]['actor_linear_velocity']=[0,0,0];rows[-20]['actor_angular_velocity']=[.051,0,0]
        self.assertFalse(final_inside_gate(rows,self.verifier,**kw)['pass'])
        with self.assertRaises(ValueError):final_inside_gate(rows[:-1],self.verifier,**kw)

    def test_native_opening_provider_and_original_release_gate(self):
        import types
        from .physical_gates import release_safety_gate
        from .certificate import build_contract
        scene=types.SimpleNamespace(can=object(),box=object())
        result=release_safety_gate(scene,build_contract()['binding'],[self.row() for _ in range(50)],self.verifier,selected_finger_link_names=['fl_link7','fl_link8'])
        self.assertTrue(result['pass']);self.assertFalse(result['physical_thresholds_changed'])
        rows=[self.row() for _ in range(50)];rows[-1]['actor_linear_velocity']=[.051,0,0]
        self.assertFalse(release_safety_gate(scene,build_contract()['binding'],rows,self.verifier,selected_finger_link_names=['fl_link7','fl_link8'])['pass'])

    def test_correctly_rehashed_but_reordered_native_registry_rejected(self):
        c=copy.deepcopy(self.c);c['can_shapes'][0],c['can_shapes'][1]=c['can_shapes'][1],c['can_shapes'][0]
        c['receipt_sha256']=digest({k:v for k,v in c.items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):validate_certificate(c)

    def test_old_verifier_still_fails_saved_contact_pose(self):
        from controlled_multi_future.geometry import compose_pose,obb_inside_local_cavity
        from .certificate import P,load
        m=load(P/'assets/objects/071_can/model_data0.json');center=np.asarray(m['center'])*m['scale'];half=np.asarray(m['extents'])*np.asarray(m['scale'])/2
        old=obb_inside_local_cavity(compose_pose(self.pose,[*center,1,0,0,0]),half,self.box,self.c['unchanged_strict_lower_m'],self.c['unchanged_strict_upper_m'])
        self.assertFalse(old['pass_true_cavity_obb'])

if __name__=='__main__':unittest.main()
