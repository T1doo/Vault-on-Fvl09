# runtime-v3_3 finite nonformal scope budget v1.1

状态：`user_authorized_pre_stage0_nonformal_v3_3`。

V1.1 只把 eligible device scope 从 physical GPU0 扩展到 physical GPU0–7，并允许不同空闲卡上的独立 family jobs 并行；所有 planner/execution/timeout/revision 数值与 V1 完全相同。

公共规则：每次仅选择实时 independently fresh-idle 的卡；每卡一 job；显式 physical-index/UUID 绑定；独立 immutable namespace/process tree/cleanup receipt；`automatic_retry=false`；`recovery_attempts=0`；失败证据 append-only；每 family 最多 2 个新 revisions，每 revision 最多 1 次完整 root。

| Scope | Planner 上限 | Execution 上限 | Timeout | 停止线 |
|---|---:|---:|---:|---|
| canonical-prefix real smoke | 16 | 1 | 1800 s | exact replay/current/anchor 任一失败即停 |
| F4 cube grasp no-action/IK | 24 | 0 | 1800 s | A/B/C 任一无效或不可达即停 |
| F1 planner/root per revision | 64 | 3 | 5400 s | planner 3/3 后才执行；root失败消耗revision |
| F2 diagnosis/root per revision | 96 | 4 | 7200 s | geometry Gate先行；root失败消耗revision |
| F3 prefix/root per revision | 160 | 4 | 10800 s | shared-prefix Gate先行；root失败消耗revision |
| F4 block/root per revision | 256 | 10 | 20400 s | A/B/C单块先行；完整root失败消耗revision |

这些上限是 v3_3 nonformal safety envelope，不是 Stage 0 attempt budget，也不批准正式采集。并行不合并、不放大任何单 scope 或 revision 预算。

计数语义保持不变：`planner_query_limit`覆盖 canonical-prefix reference planner、grasp-target selection planner 与所有 suffix/diagnostic planner query 总和。计数单位为一次官方 planner API call；`left/right_plan_multi_path`的一次batch call计1，同时把其10个内部pose candidates另存为`internal_pose_candidate_count`，不得隐去。每个 fresh scene 另有更小的 pre-call cap。`execution_limit`只计 semantic diagnostic/candidate suffix execution attempts；canonical-prefix reference generation与exact prefix replay分别记录。任一 missing/negative/non-integer count均 fail closed。
