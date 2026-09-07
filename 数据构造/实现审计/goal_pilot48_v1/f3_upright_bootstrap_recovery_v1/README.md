# F3 upright initialization-boundary implementation recovery V1

CPU implementation and regression complete; no GPU, reservation, physical rollout or new qualification success is claimed here. `runtime.py` and `test_all.py` are frozen following session 57670: exit 0, 39 tests in 1.520 s (6 new regressions plus the prior 33 qualification/issuance/HD tests).

## Cause and bounded correction

The real HD001 failed during initialization, before standing, IK, grasp or video capture. `AuditScene.setup_demo` directly calls its superclass `_init_task_env_`, bypassing the nested `CountedUpright._init_task_env_` override. Consequently the old local setup depth stayed zero during initialization gripper opening. The global live meter already wraps the actual `Base_Task._init_task_env_` entry and correctly identifies this scope.

The new private Counts factory reads that actual live meter's nonnegative integer `setup_depth`. Only a positive depth exempts initialization calls from task-action counting. At zero, a real nonempty trace remains mandatory, regardless of the legacy local depth; invalid/missing depth fails closed. All other counters and caps remain inherited unchanged. Private function-global/module copies inject the factory into the frozen HD wrapper and qualification runtime without mutating either original module.

The new tests execute the exact frozen nested `CountedUpright` AST against a CPU direct-super MRO fixture: old rejection is reproduced; the new boundary permits setup only; later untraced actions are rejected even with fake positive local depth; setup exceptions unwind; valid task actions count once. A separate test verifies the actual private factory injection leaves frozen module globals intact. This fixture does not construct SAPIEN scenes or prove physical or rendering success.

## Impact and finite next step

Same selected B design/seed/asset, mass/inertia/friction/collision geometry, close 0.50, 25 mm lift, original 20 mm/5 mm/0.05 rad/50-frame gates, full native controls checks, 960×720 independent HD camera views and original 900 s child cap remain unchanged. The existing after-setup 6000-step cap is unchanged; uninstrumented setup_scene internal steps remain unknown, not falsely counted.

The consumed HD001 result remains 0 solver / 1 fresh scene / 0 action / 0 collection and 33 lease seconds with verified cleanup. Recovery issuance is exclusively the main scheduler's responsibility: at most 6 solver / 1 fresh scene / 1 action / 0 collection / 1080 lease seconds, retaining prior failure consumption. This recovery can bring cumulative fresh scenes to two; it does not authorize a third cumulative scene for successful confirmation or shared V. No old stability-revision count is reset.

Current source interface is `run(manifest, *, meter)`, compatible with `runtime/issue_upright_bootstrap_recovery.py`. It requires the exact HD001 parent, retained failed scene count and explicit absence of confirmation authorization, then delegates to all existing first-qualification scope checks. Existing qualification and HD terminal records remain the authoritative runtime outputs. The newly issued manifest's source hash binds this recovery implementation; no earlier receipt is rewritten.

No known remaining mandatory CPU correction at handoff. Actual Guard-controlled setup and HD operation remain to be verified in the finite recovery run.
