# 共享审阅要求与 runtime-v3_3 当前实现映射

来源：用户于 2026-08-30 指定的 ChatGPT 共享审阅 `t_6a92c191fe588191becfca13f19eb54c`。该审阅描述的是 runtime-v3_2 终止后、accepted root 仍为 0 时的下一版要求；以下以当前服务器证据为准，不倒退覆盖后来实现。

## 已完成的公共要求

- `CanonicalPrefixArtifactV1` 已实现：prefix 只在 reference scene 规划一次，26-D/250 Hz effective-setpoint bytes 在三条 fresh scene 中逐步重放。
- 三分支硬检查 actual prefix action SHA、step count、prefix-end anchor/physical equivalence；settling 与 semantic P 分账。
- suffix planner 从真实 replay prefix-end qpos 开始；preflight 与 rollout 使用 frozen suffix artifact/control cache。
- same-current、physical anchor、candidate freeze、raw N/N+1、receipt、cleanup/orphan、source lock 与 GPU Guard 已接入真实 SAPIEN root 管线。
- F1 red/green/blue 三分支完整 root 已 accepted，当前 accepted nonformal pre-Stage-0 roots 为 `1/4`。

## 仍在收敛的 family

| Family | 共享审阅当时 blocker | 当前 revision-4 证据 | 下一 source-distinct 修复 |
| --- | --- | --- | --- |
| F2 | inside dynamics、region overlap、strict prefix | strict prefix 与三区 suffix planner 已通过；三分支均被合法 EEF palm `fl_link6` 的 contact-classification 假阳性截停 | F2-specific palm topology whitelist；finger-only grasp continuity 保持不变 |
| F3 | shared-V、slip、strict prefix | 所有已执行 V/H event、order、free-space contact 均通过；失败集中在 return/release disengagement；一条 branch 因运行期间瞬时 source rewrite 触发 reconstruction hash mismatch | return controls time dilation、1 cm contact-free release、actual disengagement Gate、sealed source hash与详细 mismatch receipt |
| F4 | procedural RGB cube grasp | common-X prefix 与 A 七段 planner 通过；但 prefix-end finger 卡 tray，A grasp tracking error 84.9 mm，cube 未离桌，pregrasp 又直接推移 common-X 35.4 mm | 先修 common withdraw/high neutral 和 actual-aperture/contact boundary；再做 top-down A 20 mm micro-lift Gate |

## 当前裁决

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
accepted_nonformal_pre_stage0_roots: 1
stage0_authorized: false
stage0_trajectory_count: 0
stage1_trajectory_count: 0
formal_trajectory_count: 0
h_reveal: null
```

只有 F1–F4 各有一个 same-current、fresh-scene、3/3 branch、严格 verifier、cleanup 全通过的 accepted root，才生成但不执行 Stage 0 审批包。
