"""Bounded support-first sequence; no scene creation or implicit retry."""
from .spec import validate_spec

def execute(backend,spec):
    validate_spec(spec);before=backend.solver_query_count;events=[];released=False
    def require(row,label):
        events.append({'stage':label,'receipt':row})
        if row.get('pass') is not True:raise RuntimeError(label+' rejected')
    try:
        require(backend.install_carried_fullworld(),'carried_fullworld')
        for i in range(3):
            if i==1:require(backend.install_carried_fullworld(),'actual_postlift_carried_fullworld')
            if i==2:require(backend.install_floor_only(),'floor_only')
            require(backend.plan_one(i),'plan_'+str(i))
            require(backend.screen_carried(i),'native_'+str(i))
            require(backend.execute_one(i),'execute_'+str(i))
        backend.wait_and_record(50)
        require(backend.support_gate(),'original50_support_and_actual_floor')
        for target in (.2,.4,.6,.8,1.):
            if target==1.:require(backend.release_safety_gate(),'ReleaseSafetyGateV10_before_full_open')
            backend.open_gripper(target)
            if target==1.:released=True
            backend.wait_and_record(10)
        backend.begin_settle();backend.wait_and_record(250)
        require(backend.install_released_fullworld(),'actual_released_open_fullworld')
        for i in (3,4):
            require(backend.plan_one(i),'plan_'+str(i))
            require(backend.execute_one(i),'execute_'+str(i))
        backend.wait_and_record(75);require(backend.final_gate(),'native_floor_and_original_final_V10')
        result={'pass':True,'error':None}
    except Exception as e:result={'pass':False,'error':{'type':type(e).__name__,'message':str(e)}}
    used=backend.solver_query_count-before
    if not 0<=used<=5:result={'pass':False,'error':{'type':'SolverAccountingError','message':str(used)}}
    result.update(events=events,solver_problems=used,independent_ik_problems=0,scene_creation_attempts=0,
      containing_fresh_scene_budget=1,collection_attempts=0,full_open_executed=released,
      old_gravity_drop_used=False,whole_root_pass=False)
    return result
