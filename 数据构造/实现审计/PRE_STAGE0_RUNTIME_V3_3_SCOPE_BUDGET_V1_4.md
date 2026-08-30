# runtime-v3_3 pre-Stage-0 scope budget v1.4

状态：`approved=true`、`frozen=true` 仅表示用户已批准本轮 revision-5 非正式修复 envelope；`stage0_authorized=false`。

| Scope | Planner 上限 | Execution 上限 | Timeout | Source-bound static envelope |
| --- | ---: | ---: | ---: | ---: |
| F2 revision-5 full root | 96 | 4 | 7200 s | 32 / 3 |
| F3 revision-5 full root | 160 | 4 | 10800 s | 96 / 3 |
| F4 revision-5 common-boundary + A micro-lift | 16 | 1 | 7200 s | 13 / 1 |

F4 完整 staged/full scope 的静态 planner envelope 因两个 prefix reference 各新增一个 withdraw segment，由 116 更新为 118；本轮不执行该 scope。

所有 scope：单次授权、无自动 retry、recovery=0、失败 namespace 永久保留。用户允许继续建立后续 source-distinct revision，不等于允许在同一 revision 中无限重试。

Budget receipt SHA-256：`ec79e21abc2a2e4c71f47a49df59f6c37c6a8db2bbaf752ac3b28c6af482b535`。
