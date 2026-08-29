# controlled_multi_future_runtime_v3_3 implementation proposal

## 目标

先修复公共 strict-prefix 与 planner/execution 一致性，再处理四个 family terminal blocker。科学设计仍为 `controlled_multi_future_f1_f4_v1_2`。

## 公共架构

```text
pristine current/anchor
→ task/physical audit
→ candidate universe freeze once
→ canonical prefix 只规划/执行一次
→ seal CanonicalPrefixArtifactV1
→ 3 fresh scenes replay exact 26-D prefix bytes
→ prefix-end physical equivalence Gate
→ suffix 从真实 replay-end qpos 规划
→ execute frozen suffix targets
→ raw/verifier/root finalizer
```

新增版本化模块：

```text
canonical_prefix_artifact_v1.py
canonical_prefix_replay_v1.py
root_orchestrator_v1_2.py
project_cube_grasp_pose_v1.py
```

## Family 修复

- F1：三色公平 reachability impact review；只允许三色共用规则。
- F2：inside release dynamics diagnosis；冻结互斥 facility-local predicates/layout。
- F3：共享 prefix=`grasp/lift/central/first-V`；统一 V primitive 与 grasp boundary。
- F4：procedural cube 固定 right-arm local grasp transform；preflight 与 rollout 执行同一 frozen targets。

## Gate

任何 root 只有同时满足 same-current/anchor、freeze once、3/3 task/physical、3/3 suffix planner from actual prefix-end、3/3 exact prefix replay、3/3 raw/verifier/cleanup 和 root finalizer accepted，才记为 accepted。

本 proposal 不授权 Stage 0；Stage 0 审批包只在四个 family 各有一个 accepted root 后生成，且保持 `approved=false/stage0_authorized=false`。
