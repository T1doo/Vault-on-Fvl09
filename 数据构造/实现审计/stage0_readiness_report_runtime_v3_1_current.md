# Stage 0 readiness — runtime-v3_1 v5.1 current

## BLOCKED_WITH_REASONS

真实 A0 Gate 已在全新 postmortem-validation namespace 下通过。Run1 与 run2 的历史失败证据保持不变；用户根据 GPT 对 postmortem 修复的审阅，单独批准了第三次、one-shot、A0-only 验证。Run3 在 physical GPU0 上完成 `A0_pristine + A0_fresh_1/2/3` 四个唯一 scene，全部 cleanup 成功且 task-owned orphan=0。

Run3 的四个 current hash 均为 `10d9c15aa3740cd1abc9cbb6f2d4d345dfd97f47e66d2119af3c00d5210271c8`，四个 physical anchor hash 均为 `0f8444b2ffa243ed1a2bfd40e39ad047fe1fd1b05ce64664b1cc1c7bc2d9540d`。每场 wrapper/native planner、controlled action、post-setup physics step 均为0；16/16被引用artifact已独立重哈希通过。Guard无timeout，process-group/scene orphan均为0，GPU0最终回到P8、14 MiB、0%且无compute process。

因此当前硬阻塞：

1. F1 3/3、F2 inside/on/beside 3/3、F3三个完整program、F4三个完整program仍缺真实证据；
2. 真实root pipeline尚未运行；
3. Stage 0 manifest与attempt budget不能根据缺失的family probe伪冻结。

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

不得启动 Stage 0。本次新A0授权已消费，不可重放；它没有自动授权F1–F4 action probes。下一安全动作是单独审阅并批准有限的family nonformal scopes，然后依次补齐F1–F4与真实root证据。
