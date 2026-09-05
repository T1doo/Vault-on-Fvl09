"""Always retain target/scene/planner/cleanup evidence, including exceptions."""
def record_attempt(opened_scene, derive, plan, write_receipt):
    context=None; scene=None; target=None; result=None; error=None
    before=after=None
    try:
        with opened_scene() as (scene,context):
            before=int(getattr(scene,"planner_query_count",0))
            try:
                target=derive(scene)
                result=plan(scene,target)
            finally:
                after=int(getattr(scene,"planner_query_count",before))
    except Exception as exc:
        error={"type":type(exc).__name__,"message":str(exc)}
    finally:
        cleanup=None if context is None else context.cleanup_receipt
        receipt={"scene_instance_id":None if cleanup is None else cleanup.get("scene_instance_id"),
                 "planner_before":before,"planner_after":after,
                 "planner_delta":None if before is None or after is None else after-before,
                 "target_derivation":target,"result":result,"cleanup":cleanup,"error":error,
                 "physical_execution_count":0}
        write_receipt(receipt)
    return receipt
