# runtime-v3_4_1 统一计数与终止语义

当前实现使用 `cmf_common_scope_counter_schema_runtime_v3_4_1`。planner 的预算计数是 `scope_total`，且必须满足：

```text
scope_total = canonical_prefix + target_construction
            + suffix_control_chain + diagnostic_only
```

只有 `suffix_control_chain` 表示生成可执行控制缓存的 planner query；`target_construction` 不得再伪装成 control-chain query。F1 的既有机器证据固定为每分支 `4 target-construction + 11 suffix-control = 15`。

execution lifecycle 分成 `dispatch_started → controller_entered → terminal_receipt_written`，计数必须单调，且预算以调用 controller 前已持久化的 `dispatch_started` 为准。

primary failure、cleanup 和 receipt propagation 互不覆盖。缺少 joint/contact/current/raw 等必需证据时，终止类型是 `infrastructure_schema_failure`，不得记为物理失败或 predicate=false。

实现文件：`controlled_multi_future/common_scope_counter_schema_v3_4_1.py`。当前 source SHA-256 为 `81c8603699c2fa086f524cb313e17aca205f00a575e7cc92588de6576c120ffc`。
