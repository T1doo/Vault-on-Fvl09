# F1–F4 implementation registry — Stage 0 smoke v1.1 CPU current

Base asset/physics/verifier registry继续引用`f1_f4_implementation_registry_v3_1_cpu_current.md/json`及后续runtime-v3_4_1 terminal evidence；本版本不修改资产、物体ID、arm、layout、program或verifier。

| Family | v1.1变化 | Stage 0入口状态 |
|---|---|---|
| F1 | 无；继续使用RGB blocks、plastic box、left arm与严格prefix/verifier | ready，Stage 0可记录成功或失败 |
| F2 | 无；固定071_can/base1与left arm，不放宽inside/on/beside verifier | 带已知final-inside风险进入Stage 0 |
| F3 | 无；固定001_bottle/base13、V/H轴与VVHH/VHVH/VHHV | 带已知grasp/prefix物理风险进入Stage 0 |
| F4 | 新增immutable canonical-neutral binding v13；target spec exact，realized prefix tolerance独立 | v13 infrastructure pass；四corridor物理planner fail，以shared blocker进入Stage 0 |

F4新增代码入口：`f4_frozen_canonical_neutral_binding_v13.py`、`f4_corridor_selection_gate_v13.py`、`real_sapien_adapter_v1_7.py`。Stage 0新增manifest/budget/bundle/authorization/runner/finalizer v1.1入口，以及每条generated trajectory强制`stage0_video_capture_v1.py` MP4。Source tree SHA=`41a6ede4e2b4dea01e7587ead948358023aeae2972006c31fce076bb96b31063`。
