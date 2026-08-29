# runtime-v3_2 Stage 0前工作总授权

用户要求执行共享对话：

```text
https://chatgpt.com/s/t_6a928c7bc2b481919be3ba2b572de413
```

本授权建立新的实现版本：

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_2
formal_data: false
stage0_data: false
stage0_authorized: false
```

科学定义保持：F1 red/green/blue选择；F2同一main object执行inside/on/beside；F3 VVHH/VHVH/VHHV；F4 common-X + ABC/ACB/BAC。

授权范围：

- CPU/static证据、资产、几何、dtype、IK/planner和布局审计；
- additive runtime-v3_2实现与测试；
- F1–F4有限真实GPU/SAPIEN nonformal probes；
- RealSapienPilotRootOrchestrator真实root；
- impact reports、registry/readiness/日志；
- Vault commit/push。

当前会话GPU硬规则优先：只允许physical fvl05 GPU0，并且每次launch前仍须由atomic guard证明fresh-idle；不共享、不抢占、不干预他人进程。

新预算边界：

```yaml
maximum_new_repair_revisions_per_family: 2
F1_maximum_new_repair_revisions: 1
automatic_retry: false
recovery_attempts: 0
```

每个revision必须有独立impact、CPU tests、request、source lock、one-shot authorization、consumption、guard和output namespace；旧v3_1 authorization不可重放。

F1固定red→green→blue，12 planner queries/branch、1 execution/branch、1200秒/branch；不改场景和程序。

F2在GPU前按固定顺序建立官方资产兼容矩阵：071_can其他IDs→062_plasticbox其他IDs→较小官方main object。只能冻结排序第一的合规组合；三分支继续使用同一object、同一arm、inside/on/beside。改成非plasticbox container必须先停止并提交design-impact review。

F3先执行真实post-grasp专项诊断：pregrasp→grasp→close→hold→4cm lift→hold→full lift；真实lift planner必须读取actual post-grasp qpos。诊断1次，repair最多1次，每run planner≤16、timeout≤1800秒。Prefix lift成功后才可继续V/H、return和三个program。

F4先联合审计arm∈{left,right}、008_tray官方IDs、tray/common-X/A/B/C/slots/neutral布局；优先right-arm mirror。冻结第一个CPU geometry+real planner preflight合规组合后，按common-X→A-only→B-only→C-only→noninterference→ABC→ACB→BAC推进。

只有F1–F4各有1个accepted nonformal root后才能生成但不得执行Stage0 manifest/budget/request。

明确禁止：正式Stage0、Stage1、360条正式数据、模型训练、H_reveal、compression、π0.5，以及提交/push官方RoboTwin仓库。
