# A0 postmortem-validation 单次用户授权

用户要求执行以下共享对话中的 GPT 审阅结论：

```text
https://chatgpt.com/s/t_6a92743292b481918785f884b7a72a19
```

该共享对话审阅的 Vault HEAD 为：

```text
d56a7f8de1784d116ce169fcce1d192387992bfc
```

用户本轮明确指令为：完成该共享对话中的 GPT 要求。因此，本文件只记录对下列新 scope 的一次性授权：

```yaml
scope: A0_current_anchor_smoke
purpose: postmortem_validation
family: F1
scene_seed: 20260829
scene_pattern:
  - A0_pristine
  - A0_fresh_1
  - A0_fresh_2
  - A0_fresh_3
post_setup_planner_query_limit: 0
post_setup_controlled_action_limit: 0
post_setup_physics_step_limit: 0
timeout_seconds: 600
max_invocations: 1
automatic_retry: false
allowed_physical_gpu_indices:
  - 0
formal_data: false
stage0_data: false
stage0_authorized: false
```

必须使用以下全新且不可复用的证据链：

- 新 scope request；
- 新 source-lock receipt；
- 新 one-shot authorization；
- 新 authorization consumption receipt；
- 新 GPU guard receipt；
- 新 output namespace。

固定 output namespace：

```text
/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/nonformal_A0_F1_seed20260829_run3_postmortem_validation
```

只有以下条件全部满足时，A0 才能通过：

- 4/4 唯一 scene 均创建并独立 cleanup；
- fresh1/2/3 current 与 pristine 严格一致；
- fresh1/2/3 physical anchor 与 pristine 等价；
- wrapper/native planner delta 全部为 0；
- controlled action delta 全部为 0；
- post-setup physics step delta 全部为 0；
- scene/activity/cleanup/handle ID 一致；
- artifact hash 可重算；
- task-owned orphan 为 0；
- GPU0 返回运行前空闲基线。

如果本次 A0 失败：保存全部证据，不自动再执行，不放宽 current/anchor Gate，不运行 F1–F4，不启动 Stage 0，并停止反馈。

如果本次 A0 通过：只更新 A0 和 readiness 状态。A0 通过不自动授权 F1–F4 action probes，也不授权 Stage 0。

本授权明确不包括：

```text
F1/F2/F3/F4 action probe
real root integration
Stage 0
Stage 1
360 条正式数据
模型训练
H_reveal 裁决
compression
π0.5 / policy transfer
Git commit / push
```

旧 run1/run2 的 authorization、consumption、guard、output 和失败证据继续保持不可变，不得复用或覆盖。
