# 新会话工作交接：Stage 0 v1.2 已封存

## 新会话先读

1. `AGENTS.md` GPU规则（GPU0–7任一fresh-idle，支持不同root跨卡并行）；
2. `数据构造/正式数据构造日志.md` §205–§213；
3. `STAGE0_SMOKE_RESULT_V1_2.json`；
4. `STAGE0_SMOKE_TERMINAL_SEAL_V1_2.json`；
5. `STAGE0_SMOKE_EXECUTION_REPORT_V1_2.md/json`；
6. `stage0_readiness_report_stage0_smoke_v1_2_current.md/json`；
7. `STAGE0_F2_REPLACEMENT_V1_2_RUN2_EVIDENCE_MANIFEST_20260831.json`。

## 已完成且不得重开

- Stage 0 active 12 slots已seal为`STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`；
- F1原3条保留且全部pass；
- F2三个replacement已完成：inside fail、on/beside pass；
- F3/F4原Stage 0失败保留为有效evidence；
- 所有generated trajectories均有MP4；
- formal count=0，Stage 1未授权。

禁止重新运行F1、F2 replacement或重开/覆盖Stage 0。F2 run1 prelaunch失败与run2原始/修正派生receipts均保留。

## 下一工作包（继续共享审阅要求）

### 1. F3 post-Stage-0 impact review

先从现有partial trace生成：

```text
F3_SHARED_PREFIX_PHYSICAL_IMPACT_REVIEW_V1.md/json
```

确定首次selected-gripper contact丢失、grasp transform越界、瓶子最后pad/table接触和EEF速度未稳step。只冻结一个全program共享修复；最多运行一次`same prefix × 3 fresh scenes × no suffix` diagnostic。3/3通过后才允许一个post-Stage-0 F3 development root；不修改Stage 0 seal。

### 2. F4 layout impact review

生成：

```text
F4_POST_STAGE0_LAYOUT_IMPACT_REVIEW_V1.md/json
```

保留common-X→tray、ABC/ACB/BAC、object-slot mapping和verifier。优先只调整A/B/C positions、slot positions、branch-neutral；先CPU geometry + IK + planner-only audit，冻结一个新layout后最多一个development root。禁止在旧layout继续加corridor。

### 3. F2 pre-Stage-1 development

F2 Stage 0 seal不再重开；inside的ReleaseSafetyGateV10 failure作为post-Stage-0 family implementation问题单独审阅。不得修改已经封存的F2 replacement receipts。

### 4. Stage 1 readiness

完成F2/F3/F4 development template审计后更新统一readiness；未经用户明确批准，禁止运行48条Stage 1、360 formal、训练、H-reveal、compression或π0.5。

## GPU与环境

- 新会话会重新载入correct GPU0–7规则；
- 一张空闲即运行一个job，多张空闲可并行独立root；
- 一卡一job、root不shard；
- 每job fresh `nvidia-smi` + UUID + Guard + lease + cleanup/postcheck；
- child清除`LD_LIBRARY_PATH`并用项目CUDA 12.1。

当前source在本交接前完成533/533 active与snapshot tests、191 source + 94 test compile、byte-equal。后续任何source修改必须重新freeze、测试、同步和发布。
