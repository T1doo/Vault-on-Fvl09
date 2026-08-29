# 用户授权：runtime-v3_3 pre-Stage-0 nonformal 工作包

授权来源：用户提供的 ChatGPT 共享任务链接：

```text
https://chatgpt.com/s/t_6a92c191fe588191becfca13f19eb54c
```

用户要求依据该链接继续推进。授权范围：

- 建立 `controlled_multi_future_runtime_v3_3`；
- 实现 `CanonicalPrefixArtifactV1` 与 exact deterministic replay；
- 统一 prefix/suffix planner preflight 与真实执行状态；
- 对 F1 reachability、F2 inside/互斥区域、F3 shared-V/slip、F4 procedural cube grasp 做 CPU/static/有限 nonformal GPU 修复与验证；
- 每个 family 最多 2 个新 implementation revisions，每 revision 最多 1 次完整 root，禁止自动 retry/recovery；
- 若且仅若 F1–F4 各有 1 个 accepted nonformal root，生成但不执行 Stage 0 审批包；
- 更新 registry/readiness/log/handoff 并 commit/push Vault main。

明确禁止：正式 Stage 0、Stage 1、360 条正式数据、训练、`H_reveal`、compression、π0.5、放宽 verifier、删除 runtime-v3_2 证据、branch-specific 特殊动作。

当前 fvl05 GPU 规则仍只允许 physical GPU0；每次运行必须 fresh-idle precheck、UUID绑定、task-owned cleanup、postcheck。

```yaml
approved: true
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
formal_data: false
stage0_data: false
stage0_authorized: false
stage1_authorized: false
formal_collection_authorized: false
training_authorized: false
```
