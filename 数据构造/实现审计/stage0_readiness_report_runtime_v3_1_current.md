# Stage 0 readiness — runtime-v3_1 v5.1 current

## BLOCKED_WITH_REASONS

用户已批准全部 pre-Stage-0 nonformal 工作，但真实 A0 的冻结执行预算已耗尽且未通过：run1 因fvl05 SAPIEN sleep-state API差异失败；唯一versioned repair后的run2生成了pristine current/anchor，但被旧exact-float timestep Gate拒绝，并暴露native planner ledger未初始化。两次均cleanup/orphan/GPU-release安全，post-setup planner/control/physics均为0。

Postmortem CPU修复已完成：4 ms使用`1e-9 s`表示容差，monitor前初始化RuntimeTraceMixin-compatible空planner ledger；active/snapshot 158/158 tests通过。但该修复没有新的GPU预算和真实evidence。

因此当前硬阻塞：

1. A0 pass=false，fresh1/fresh2/fresh3未运行，same-current与anchor四场景Gate未验证；
2. A0的`1 initial + 1 repair` execution budget已耗尽；
3. F1–F4和real-root scopes因A0前置失败均未启动；
4. F1 3/3、F2 inside/on/beside 3/3、F3三个完整program、F4三个完整program仍缺真实证据；
5. Stage 0 manifest与attempt budget不能根据缺失的family probe伪冻结。

```yaml
pre_stage0_parent_authorized: true
a0_real_execution_count: 2
a0_execution_budget_exhausted: true
a0_pass: false
new_gpu_launch_authorized: false
stage0_authorized: false
stage0_trajectory_count: 0
stage1_trajectory_count: 0
formal_f1_f4_trajectory_count: 0
h_reveal: null
```

不得启动 Stage 0。下一安全动作是由用户/GPT审阅run1/run2与postmortem CPU修复，决定是否建立一个新的、独立版本与新增A0预算；旧authorization均已消费，不可重放。
