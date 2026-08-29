# runtime-v3_3 finite nonformal scope budget v1

状态：`user_authorized_pre_stage0_nonformal_v3_3`。

公共规则：physical GPU0 only；fresh-idle/UUID guard；`automatic_retry=false`；`recovery_attempts=0`；失败证据 append-only；每 family 最多 2 个新 revisions，每 revision 最多 1 次完整 root。

| Scope | Planner 上限 | Execution 上限 | Timeout | 停止线 |
|---|---:|---:|---:|---|
| canonical-prefix real smoke | 16 | 1 | 1800 s | exact replay/current/anchor 任一失败即停 |
| F4 cube grasp no-action/IK | 24 | 0 | 1800 s | A/B/C 任一无效或不可达即停 |
| F1 planner/root per revision | 64 | 3 | 5400 s | planner 3/3 后才执行；root失败消耗revision |
| F2 diagnosis/root per revision | 96 | 4 | 7200 s | geometry Gate先行；root失败消耗revision |
| F3 prefix/root per revision | 160 | 4 | 10800 s | shared-prefix Gate先行；root失败消耗revision |
| F4 block/root per revision | 256 | 10 | 20400 s | A/B/C单块先行；完整root失败消耗revision |

这些上限是 v3_3 nonformal safety envelope，不是 Stage 0 attempt budget，也不批准正式采集。

计数语义：`planner_query_limit`覆盖canonical-prefix reference planner与所有suffix/diagnostic planner query总和；每个fresh scene另有更小的pre-call cap。`execution_limit`只计semantic diagnostic/candidate suffix execution attempts；canonical-prefix reference generation与exact prefix replay分别以`reference_prefix_generation_count`、`prefix_replay_count`记录，不伪装为0，也不计为candidate execution。所有physics steps仍保存在trace/activity receipt中。任一missing/negative/non-integer count均fail closed。
