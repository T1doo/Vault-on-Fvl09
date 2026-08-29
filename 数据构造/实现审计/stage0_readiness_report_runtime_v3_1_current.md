# Stage 0 readiness — runtime-v3_1 v5.1 current

## BLOCKED_WITH_REASONS

真实 A0 Gate 已通过；随后用户授权的F1–F4有限nonformal scopes已经执行到各自停止线。没有任何family达到Stage0所需的完整3/3成功，因此当前仍为`BLOCKED_WITH_REASONS`。

A0证据保持有效：四个current hash和physical anchor hash分别一致，零post-setup activity、4/4 cleanup与16/16 artifact hash均通过。

Family结果：

| Family | 最终结果 | Planner queries | Real execution | Repair |
|---|---|---:|---:|---:|
| F1 | task/physical 3/3通过并freeze一次；三候选planner在Float/Double接口失败 | 0 | 0 | 2/2耗尽 |
| F2 | 071_can/base1最小完整直径大于box严格cavity短轴 | 0 | 0 | 无合理repair |
| F3 | pad与trace修复后14段preflight成功；真实抓瓶后prefix lift失败 | 28 | 1 | 2/2耗尽 |
| F4 | task/physical通过；Route1/2均在center-high失败；无合规左侧tray layout | 20 | 0 | 1；剩余repair无合规候选 |

因此当前硬阻塞：

1. F1/F3已耗尽repair预算仍失败；
2. F2存在固定asset/full-OBB物理不兼容；
3. F4没有满足当前布局约束的tray impact candidate；
4. accepted real root=0；
5. Stage 0 manifest、budget与approval request不得在这些前置失败下生成。

```yaml
pre_stage0_parent_authorized: true
a0_real_execution_count: 3
a0_execution_budget_exhausted: true
a0_pass: true
new_gpu_launch_authorized: false
stage0_authorized: false
stage0_trajectory_count: 0
stage1_trajectory_count: 0
formal_f1_f4_trajectory_count: 0
h_reveal: null
```

不得启动 Stage 0。下一安全动作是用户/GPT对四个terminal blocker做impact review；任何进一步GPU工作都需要新的设计/实现版本、明确repair方向和新授权，不能重放本轮receipt或扩大现有预算。
