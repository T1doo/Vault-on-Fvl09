"""Per-scene native planner evidence, separate from replayed query provenance."""
from contextlib import contextmanager
from copy import deepcopy
from realization_utf8_io_v1 import write_new

def count_queries(scene):
    count=getattr(scene,'planner_query_count',None)
    rows=deepcopy(getattr(scene,'planner_queries',None))
    if type(count) is not int or not isinstance(rows,list):raise ValueError('native planner count unavailable')
    if count<0 or any(not isinstance(r,dict) for r in rows):raise ValueError('invalid native planner ledger')
    actual=[r for r in rows if r.get('replayed_from_frozen_suffix_artifact') is not True]
    if count!=len(actual):raise ValueError('actual and replay query provenance conflated')
    ids=[r.get('query_id') for r in actual]
    if any(type(i) is not int for i in ids) or ids!=list(range(1,count+1)):
        raise ValueError('native query IDs missing, duplicated or out of order')
    batch=[r for r in actual if r.get('query_type')=='batched_grasp_target_selection']
    if any(type(r.get('batch_size')) is not int or r['batch_size']!=10 or len(r.get('ordered_goal_poses',[]))!=10 for r in batch):raise ValueError('batch goal N changed')
    if any(r.get('query_type')!='batched_grasp_target_selection' and r.get('batch_size',1)!=1 for r in actual):
        raise ValueError('unrecognized multi-goal query topology')
    return dict(planner_api_calls=count,solver_problems=sum(r.get('batch_size',1) for r in actual),
        actual_query_rows=actual,replayed_query_rows=len(rows)-len(actual))

@contextmanager
def instrument_scene_ledger(adapter,output):
    original=adapter.scene;records=[];had='scene' in vars(adapter);override=vars(adapter).get('scene')
    class Context:
        def __init__(self,inner,phase):self.inner=inner;self.phase=phase;self.scene=None
        def __getattr__(self,name):return getattr(self.inner,name)
        def __enter__(self):
            h=self.inner.__enter__();self.scene=h.scene
            from controlled_multi_future.real_sapien_adapter_v1_2 import _initialize_a0_native_planner_counters
            try:_initialize_a0_native_planner_counters(self.scene)
            except BaseException as exc:
                self.inner.__exit__(type(exc),exc,exc.__traceback__);raise
            return h
        def __exit__(self,*args):
            record=dict(phase=self.phase,scene_instance_id=getattr(self.scene,'_cmf_scene_instance_id',None))
            try:record.update(count_queries(self.scene));record['accounting_complete']=True
            except BaseException as exc:record.update(accounting_complete=False,error={'type':type(exc).__name__,'message':str(exc)})
            try:return self.inner.__exit__(*args)
            finally:
                record['cleanup']=self.inner.cleanup_receipt;records.append(record)
                write_new(output/f'{len(records):02d}.json',record)
    def factory(planned,*,phase,program=None):return Context(original(planned,phase=phase,program=program),phase)
    adapter.scene=factory
    try:yield records
    finally:
        if adapter.scene is not factory:raise RuntimeError('scene ledger wrapper was not restored after collection hook')
        if had:adapter.scene=override
        else:delattr(adapter,'scene')
