# A0 用户审批请求 — runtime-v3_1 hardening v5

## 当前请求状态

```yaml
status: pending_user_approval
approved: false
gpu_probe_authorized: false
stage0_authorized: false
formal_data: false
stage0_data: false
```

本文件只把一次真实 A0 所需的 family、seed、代码、预算、guard、输出和单次消费规则准备齐全。它不是批准文件，也没有生成 `authorization_consumed`、guard receipt 或真实 A0 output。

机器请求见：`A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.json`。

## 请求的唯一运行

```yaml
scope: A0_current_anchor_smoke
family: F1
scene_seed: 20260829
scene_pattern:
  - A0_pristine
  - A0_fresh_1
  - A0_fresh_2
  - A0_fresh_3
post_setup_planner_query_limit: 0
post_setup_controlled_action_limit: 0
timeout_seconds: 600
max_invocations: 1
```

允许的 GPU 仍只是“物理 GPU0–7 中运行前由 atomic guard 证明 independently fresh-idle 的一张卡”；不预留、不共享、不抢占。实际 index/UUID 必须同时写入 guard 与 A0 receipt。

## 精确锁定

```yaml
reviewed_content_commit: 3e7cba9e1dc798f9e18a1c23e4811c80f664bf1a
implementation_source_sha256: 1aace10635af7d4aa1c371ac0818249081a83d55623871eaf5346b3af2810ab0
a0_orchestrator_sha256: bbcb7521581886b7520a075a7846eba15cf5d7373f3a318ac43768b6e7eb8a1f
a0_activity_monitor_sha256: aaf4c6399bddf3b13ef9bacddda9dfbb22a7ed0baffb50154e614852f99e7154
real_adapter_sha256: 5b7493ada5c9a6b838d3257fe1dde5a00fb637a539513e89a007387df30ff0eb
gpu_guard_sha256: 27e8468121c3d213bf3cea7c44e7beebee02f0890244d4462eb509fb5deecced
budget_receipt_sha256: c793faf2f3017fbd1b9b52dc4a7f71262ff5fa73ae2286f7873691f9101d1cd0
scope_budget_sha256: 421651cbb3302b3e38e5fe4c3151ff373b9ae1c3bea31a3d07fb216d07a91e0f
planned_root_slot_spec_sha256: 74015a6618887203b1feacc88c69ebef9afcdd34601bb7dab91673f834280a20
exact_child_command_sha256: 14110813a06cfb260da723809700d29cfd30c7e7b783c08c346842db476f5017
approval_request_sha256: 0e845b6f694a696b8a21f56f00590679e90e0fefd3de126d8b9675c0646baade
```

任何 source、budget、family、seed、planned spec、timeout、output namespace 或 child command 改变，当前请求失效，必须重新审阅。

## 单次授权与消费

用户若批准，仍需另行生成一份 `cmf_runtime_v3_1_gpu_authorization_v1_1` receipt，并填写真实 `issued_at/expires_at`、`approved=true` 和最终 `receipt_sha256`。本轮未生成该文件。

Guard 在 fresh-idle precheck 通过后、child 启动前，使用 `O_CREAT | O_EXCL` 原子创建：

```text
数据构造/实现审计/authorization_consumed/runtime_v3_1_v5/
  <authorization_id>.json
```

同一 authorization 第二次使用必然失败。即使首次 child 后续失败，该 authorization 仍视为已消费。

## 运行时固定路径

```text
future authorization receipt:
/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/authorizations/runtime_v3_1_v5/A0_F1_seed20260829_authorization_v1_1.json

future output namespace:
/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/nonformal_a0_runtime_v3_1_v5_f1_seed20260829_run1

future guard receipt:
/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/nonformal_a0_runtime_v3_1_v5_f1_seed20260829_run1.guard.json
```

精确 child command 与带动态 fresh-idle index/UUID 占位符的 guard command template 已封存在机器 JSON 中。CLI 不允许调用者覆盖 family、seed、timeout、scope 或 output namespace。

## 成功条件

- 四个唯一 fresh scene 均创建并完成 scene-bound cleanup；
- fresh1/2/3 current 与 pristine current 严格一致；
- physical anchor 在冻结 tolerance 下等价；
- 每个 `cmf_a0_activity_audit_v2` 均为 post-setup planner/control/physics delta 0；
- wrapper installation/restoration、activity/cleanup/handle identity 和 receipt one-use 均通过；
- 每个 scene artifact hash 可重算；
- 没有 task-owned orphan，GPU postcheck 回到 baseline。

任一失败立即终止，不继续后续 scene。

## 该批准不包含

- F1/F2/F3/F4 action probe；
- real root integration；
- Stage 0／Stage 1／360 条 formal collection；
- 训练、compression 或 π0.5。

## 用户决策位置

当前保持：

```text
WAITING_FOR_EXPLICIT_USER_DECISION
```

只有用户在审阅 V5 handoff 后明确批准“一次 A0”时，才可据机器模板生成最终 approved authorization receipt。未经该明确批准，禁止运行。
