"""Caller-owned fresh canonical scene -> one on/beside suffix, no collector."""
from pathlib import Path
from .spec import build_targets,validate,lineage,digest
from .controller import execute
from .models import LiveModels
from . import gates

class LiveBackend:
    def __init__(self,scene,spec,output):
        self.scene,self.spec=scene,spec;self.models=LiveModels(scene,output,spec)
        self.before=scene.planner_query_count;self.plans={};self.held_start=len(scene.trace)-1;self.windows=[];self.transport=None
        self.opened=False;self.settle_start=None;self.settle_end=None
    @property
    def solver_query_count(self):return self.scene.planner_query_count
    def install_carried(self,index):return self.models.install_carried(index)
    def plan_one(self,index):
        from controlled_multi_future.family_runners_v3_1 import _plan_chain
        if index in self.plans or self.solver_query_count>=self.before+4:raise ValueError('one attempt per four segments')
        self.models.save('plan_'+str(index)+'_start',{'target':self.spec['targets'][index],'solver_query_before':self.solver_query_count})
        try:
            plan=_plan_chain(self.scene,[self.spec['targets'][index]],query_limit=self.before+4,arm='left');self.plans[index]=plan
            return self.models.save('plan_'+str(index)+'_done',{'pass':plan.get('pass') is True,'segment_receipts':plan.get('segment_receipts',[]),'error':None})
        except Exception as e:
            self.models.save('plan_'+str(index)+'_done',{'pass':False,'error':{'type':type(e).__name__,'message':str(e)}});raise
    def screen_carried(self,index):
        result=self.models.screen(self.plans[index]['controls'][0],index)
        return self.models.save('native_'+str(index),result)
    def execute_one(self,index):
        from controlled_multi_future.high_level_physical_runner_v1 import _execute_planned_segment
        start=len(self.scene.trace)-1
        receipt=_execute_planned_segment(self.scene,self.plans[index]['controls'],[self.spec['targets'][index]],0,'left')
        end=len(self.scene.trace)-1
        if index<2:self.windows.append({'segment_id':self.spec['targets'][index]['segment_id'],'start_trace_row':start,'end_trace_row':end,
          'start_relative_to_held_transport':start-self.held_start,'end_relative_to_held_transport':end-self.held_start})
        return self.models.save('execute_'+str(index),{'pass':True,'original_execution_receipt':receipt,'start_trace_row':start,'end_trace_row':end})
    def held_gate(self):
        self.transport=gates.held(self.scene,self.spec,self.held_start,self.windows)
        return self.models.save('original_held_gate',self.transport)
    def full_open(self):
        from controlled_multi_future.high_level_physical_runner_v1 import _must_action,_arm_tag
        if self.transport is None or self.transport.get('pass') is not True:raise ValueError('held Gate required before opening')
        _must_action(self.scene,self.scene.open_gripper(_arm_tag('left'),pos=1.),'f2_'+self.spec['relation']+'_full_open')
        self.opened=True;self.settle_start=len(self.scene.trace)
    def wait_and_record(self,n):
        from controlled_multi_future.high_level_physical_runner_v1 import _wait_and_record
        _wait_and_record(self.scene,n)
        if n==100:
            self.settle_end=len(self.scene.trace)
            if self.settle_start is None or self.settle_end-self.settle_start!=100:raise ValueError('actual100-frame release settle required')
    def install_released(self):
        if not self.opened or self.settle_end is None or len(self.scene.trace)!=self.settle_end:raise ValueError('actual full-open/100settle before released model')
        return self.models.install_released()
    def final_gate(self):return self.models.save('original_final_gate',gates.final(self.scene,self.spec,self.transport))

def run(scene,replay,*,relation,output,current_sha256,initial_anchor_sha256,initial_anchor_equivalence=None):
    from controlled_multi_future.family_runners_v3_3 import F2ControllerV3_3
    from realization_utf8_io_v1 import write_new
    before=scene.planner_query_count
    try:
        source=lineage();ref=source['anchor']['anchor_sha256']
        if current_sha256!=source['current']['aggregate_sha256']:raise ValueError('strict current lineage differs')
        eq=initial_anchor_equivalence
        if eq is None:
            if initial_anchor_sha256!=ref:raise ValueError('different anchor needs original physical equivalence receipt')
        elif eq.get('equivalent') is not True or eq.get('failures')!=[] or eq.get('reference_sha256')!=ref or eq.get('candidate_sha256')!=initial_anchor_sha256:
            raise ValueError('actual/reference anchor equivalence binding mismatch')
        prefix=F2ControllerV3_3.validate_replayed_prefix_physical(None,scene,replay)
        if prefix.get('pass') is not True:raise ValueError('fresh original prefix physical Gate failed')
        spec=build_targets(scene,relation);validate(spec);write_new(Path(output)/'suffix_spec.json',spec)
        result=execute(LiveBackend(scene,spec,output),spec);result.update(spec=spec,fresh_prefix_gate=prefix)
    except Exception as exc:
        result={'pass':False,'error':{'type':type(exc).__name__,'message':str(exc)},'solver_problems':scene.planner_query_count-before,
          'scene_creation_attempts':0,'collection_attempts':0,'whole_root_pass':False,'cleanup_owned_by_caller':True}
    result['relation']=relation;result['receipt_sha256']=digest(result)
    write_new(Path(output)/'suffix_terminal.json',result);return result
