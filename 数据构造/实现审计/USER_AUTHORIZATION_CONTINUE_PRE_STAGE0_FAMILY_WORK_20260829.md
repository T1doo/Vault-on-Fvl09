# 继续完成 A0 后全部 Stage 0 前置工作的用户授权

用户要求执行共享对话：

```text
https://chatgpt.com/s/t_6a927b38b0a081918c1bc4fbdfa3125b
```

该对话确认A0已经通过，并明确授权连续完成以下nonformal / pre-Stage-0工作：

```yaml
approved_scopes:
  - Vault_commit_and_push
  - F1_three_branch_nonformal_probe
  - F2_workspace_and_three_branch_nonformal_probe
  - F3_release_and_full_program_nonformal_probe
  - F4_common_carry_and_full_program_nonformal_probe
  - real_sapien_root_integration_nonformal_probe
  - stage0_manifest_and_budget_preparation

allowed_physical_gpu_indices:
  - 0

maximum_versioned_implementation_repairs_per_family: 2
automatic_unbounded_retry: false
```

F1固定：red→green→blue，每branch execution≤1、planner query≤12、timeout≤1200秒、recovery=0；F1同时作为第一份真实root-level integration。

F2固定：071_can/base1、同一左臂、inside/on/beside。BESIDE最多6个预注册pose、16次planner query、1次execution、1200秒；若stand失败，只允许一个经CPU impact review选定的stand-layout或官方pot revision，不能连续试两个。

F3固定：001_bottle/base13、同一执行臂、V=table-z、H=table-x、VVHH/VHVH/VHHV。先1次diagnosis；按诊断最多1次条件式repair；每run planner≤16、timeout≤1800秒、无自动重试。

F4固定：common-X→tray，随后ABC/ACB/BAC。Route1 terminal non-cleanup failure后才允许fresh-scene Route2；每route execution≤1、planner≤16、timeout≤1800秒。两个route失败后最多一个tray-layout impact revision。当前禁止strict array-splice reorder。

每个真实root必须通过`RealSapienPilotRootOrchestratorV1_1`，不可用零散action script人工拼接。每个GPU run必须有独立scope request、source lock、one-shot authorization、atomic consumption、guard、output namespace与terminal receipt。

只有F1–F4全部通过后，才允许生成但不执行：

```text
STAGE0_EXECUTION_MANIFEST_V1.md/json
STAGE0_ATTEMPT_BUDGET_V1.md/json
STAGE0_USER_APPROVAL_REQUEST_V1.md/json
```

Stage0 proposal固定4 families × 1 root/family × 3 intents/root × only r_pc = 12 trajectories，且必须保持`approved=false / stage0_authorized=false / formal_data=false`。

本授权明确禁止：

```text
正式Stage 0执行
Stage 1
360条正式轨迹
模型训练
H_reveal裁决
compression
π0.5或policy transfer
提交或push官方RoboTwin仓库
```

允许在全部工作完成或有限预算耗尽后，同步byte-equal Vault snapshot，更新文档，并commit/push Vault main。
