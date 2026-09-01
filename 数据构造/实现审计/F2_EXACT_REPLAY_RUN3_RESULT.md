# F2 Exact Replay Run3 Result

终态：`ALL_12_DYNAMIC_CANDIDATES_EXHAUSTED`

- rank50–54：passive-on 与 layout 通过；inside suffix planner IK failure，未执行分支。
- rank55–59：passive-on angular stability failure；未进入 planner。
- rank60–61：passive-on support、linear stability、angular stability failure；未进入 planner。
- 总计：12 candidates、125 planner queries、5 prefix references、0 branch executions、0 recovery。
- Passing binding：无；inside/on/beside development root：无。
- GPU2 Guard：completed，child exit 0，timeout=false，task-owned cleanup/source-lock/lease/cache/post-release 全部通过，orphan=0，GPU2 返回 `14 MiB/0%/P8/no process`。

Machine result：`F2_EXACT_REPLAY_RUN3_RESULT.json`，payload `9181d6e8840ab843bd58a8b98e8406625a8c3bd8365fde6102c3b39956ae9664`。

该结果只支持“当前冻结 12 个 asset/layout candidates 已耗尽，需要更高层 asset/layout redesign”；不授权在本工作包扩大候选，也不改变 Stage 1/formal/training 禁止边界。
