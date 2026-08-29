# Stage 0 readiness：runtime-v3_3 revision-3 CPU current

## BLOCKED_WITH_REASONS

F1 已形成一个完整 accepted nonformal pre-Stage-0 root。F2/F3/F4 revision-2 均留下安全、不可变的终止证据；用户已授权继续进行source-distinct versioned repairs。Revision-3 CPU实现与审阅快照现均 `287/287` 通过，且多代理P0 sweep没有发现可复现的GPU前blocker；但revision-3尚未真实运行，因此仍不能批准Stage 0。

### 已具备

- F1 red/green/blue 三fresh branches accepted；
- F2 dynamic-settle修复已被r2真实验证，r3进一步修正center-aware can geometry、inside drop route与beside candidate fairness；
- F3 r2真实轨迹已定位pad/table collision和central grasp drift，r3以geometry-derived clearance、slow same-height carry及每event support-contact Gate修复；
- F4 common-X 真实prefix完全通过，r3仅对A/B/C统一增加carry midpoint，不移动tray/layout、不换arm/program；
- root orchestrator、same-current/anchor、frozen prefix/suffix、raw/verifier/finalizer、one-shot authorization与GPU cleanup链；
- GPU0–7 任一 independently fresh-idle卡可用，独立family允许并行；
- revision-3 budget v1.2、parent authorization、source binding与revision ledger规则已完成CPU测试。

### 仍缺真实证据

```text
F2 revision-3 accepted root
F3 revision-3 accepted root
F4 revision-3 staged A/B/C/AB + accepted ABC/ACB/BAC root
四个family accepted后的真实SAPIEN pipeline dry-run总复核
```

### 当前计数

```yaml
accepted_nonformal_pre_stage0_roots: 1/4
stage0_trajectories: 0
stage1_trajectories: 0
formal_f1_f4_trajectories: 0
h_reveal: null
training_started: false
compression_started: false
pi0_5_started: false
```

### 下一安全顺序

1. 发布byte-equal revision-3 CPU baseline和r2失败证据；
2. 以clean published HEAD签发F2/F3/F4 revision-3的三个single-use scopes；
3. 在三张分别fresh-idle GPU上并行运行，完整保存成功与失败；
4. 独立审计root/trace/verifier/cleanup并更新readiness；
5. 只有四个family全部accepted且真实pipeline总复核通过，才可改为`READY_FOR_USER_REVIEW_BEFORE_STAGE_0`；仍不得自行启动Stage 0。
