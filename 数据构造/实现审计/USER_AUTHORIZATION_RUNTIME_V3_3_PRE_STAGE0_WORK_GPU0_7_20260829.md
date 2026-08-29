# 用户授权：runtime-v3_3 pre-Stage-0 nonformal GPU0–7 工作包

授权来源：用户在当前 Codex 对话中于 2026-08-29 明确指示：

> 有其他空闲gpu你可以并行跑啊这样不是快嘛

本授权只替换先前 parent authorization 中的 GPU device scope；其余科学设计、finite budget、revision stop line 与禁止项保持不变。

授权范围：

- physical fvl05 GPU0–7 中任一张 independently fresh-idle card 均可使用；
- 独立 family job 可在不同空闲卡并行；
- 每张卡最多一个本项目 job，禁止共享忙卡；
- 每个 job 必须使用独立 immutable namespace、明确 physical index 与实时 UUID、独立 process tree／cleanup／orphan receipt；
- 每次启动前和结束后均执行 fresh `nvidia-smi` 检查，任何 cleanup 或 ownership 不确定立即停止对应卡；
- 继续完成 runtime-v3_3 的有限 nonformal F1–F4 root 验证，每 family 最多 2 个 implementation revisions，每 revision 最多 1 次完整 root，禁止自动 retry/recovery；
- 若且仅若 F1–F4 各有 1 个 accepted nonformal root，生成但不执行 Stage 0 审批包；
- 更新 registry/readiness/log/handoff 并 commit/push Vault main。

明确禁止：正式 Stage 0、Stage 1、360 条正式数据、训练、`H_reveal`、compression、π0.5、放宽 verifier、删除历史失败证据、branch-specific 特殊动作、在同一 GPU 上共享或干预他人进程。

```yaml
approved: true
allowed_physical_gpu_indices: [0, 1, 2, 3, 4, 5, 6, 7]
parallel_independent_jobs: true
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
formal_data: false
stage0_data: false
stage0_authorized: false
stage1_authorized: false
formal_collection_authorized: false
training_authorized: false
```
