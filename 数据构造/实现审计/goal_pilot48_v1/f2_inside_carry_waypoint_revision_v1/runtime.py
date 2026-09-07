"""Change only carry target0; preserve approved contact and physical Gates."""
import copy
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.spec import build_targets as old_build,digest
from goal_pilot48_v1.f2_controlled_inside_runtime_v3 import runtime as supported
from .analyze import target_from_actual,clearance,sphere_clearance

def build_targets(**kwargs):
    s=old_build(**kwargs);parent=s.pop('receipt_sha256');original=copy.deepcopy(s['targets'][0])
    s['targets'][0]=target_from_actual(s);s.update(schema_version='f2_controlled_inside_carry_waypoint_revision1',parent_target_spec_sha256=parent,
      carry_waypoint_revision=1,original_unexecuted_extra_lift_target=original,final_inside_and_other_targets_unchanged=True)
    s['receipt_sha256']=digest(s);return s

class LiveBackend(supported.LiveBackend):
    def install_carried_fullworld(self):
        r=super().install_carried_fullworld()
        if self.plans:return r
        if self.spec['targets'][0]!=target_from_actual(self.spec):raise ValueError('unregistered carry waypoint/height changed')
        native=clearance(r['world'],r['can'],r['base'],self.spec,self.spec['targets'][0])
        spheres=sphere_clearance(r,self.spec,self.spec['targets'][0])
        return {'pass':bool(r['pass'] and native['pass'] and spheres['pass']),'original_full_model_receipt':r,
          'actual_native_straight_carry_bound':native,'actual_sphere_buffer_straight_carry_bound':spheres,
          'actual_planner_path_native_screen_still_required':True}

def run(*args,**kwargs):
    approval=supported.verify_approval()
    inner=supported.private(supported.old._run,LiveBackend=LiveBackend,build_targets=build_targets)
    r=supported.private(supported.old.run,_run=inner)(*args,**kwargs)
    r.update(implementation_version='f2_inside_carry_waypoint_revision_v1',carry_waypoint_revision=1,contact_design_approval=approval)
    return r
