"""Four real sequential planner attempts; execution itself is solver-free."""

def execute(backend,spec):
    before=backend.solver_query_count;rows=[]
    def gate(label,result):
        rows.append({'stage':label,'result':result})
        if result.get('pass') is not True:raise RuntimeError(label+' failed')
    def no_solver(fn,*args):
        n=backend.solver_query_count;result=fn(*args)
        if backend.solver_query_count!=n:raise RuntimeError('action/setup unexpectedly planned')
        return result
    error=None
    try:
        if spec['relation'] not in ('on','beside') or spec['settle_frames']!=100 or spec['rest_frames']!=75 or len(spec['targets'])!=4:
            raise ValueError('wrong relation/windows/segment count')
        for i in range(4):
            if i<2:gate('carried_model_'+str(i),no_solver(backend.install_carried,i))
            elif i==2:gate('actual_released_fullworld',no_solver(backend.install_released))
            n=backend.solver_query_count;gate('plan_'+str(i),backend.plan_one(i))
            if backend.solver_query_count!=n+1 or backend.solver_query_count>before+4:raise RuntimeError('exact one solver per stage required')
            if i<2:gate('native_'+str(i),no_solver(backend.screen_carried,i))
            gate('execute_'+str(i),no_solver(backend.execute_one,i))
            if i==1:
                gate('original_held_transport',no_solver(backend.held_gate))
                no_solver(backend.full_open)
                no_solver(backend.wait_and_record,100)
        no_solver(backend.wait_and_record,75)
        gate('original_final_relation',no_solver(backend.final_gate))
    except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)}
    used=backend.solver_query_count-before
    return {'pass':error is None and used==4,'error':error,'stages':rows,'solver_problems':used,
      'independent_ik_problems':0,'scene_creation_attempts':0,'collection_attempts':0,'whole_root_pass':False,
      'suffix_only':True,'cleanup_owned_by_caller':True}
