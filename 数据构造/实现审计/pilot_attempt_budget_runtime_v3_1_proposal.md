# runtime-v3_1 finite GPU budget proposal

```yaml
status: proposed_for_user_review
approved: false
frozen: false
gpu_probe_authorized: false
stage0_authorized: false
```

| Gate | Scope | Planner | Execution | Timeout | Stop |
| --- | --- | ---: | ---: | ---: | --- |
| A0 | one pristine + three fresh real SAPIEN scenes；current/anchor/cleanup/GPU release only | 0 | 0 actions | 600 s | any mismatch/cleanup uncertainty stops all |
| F1 | one real root, red→green→blue, actual identical prefix | 12/branch | 1/branch | 1200 s/branch | below 3/3 leaves F1 incomplete |
| F2 | beside only；six fixed fresh-scene planner variants；first success then one rollout | 16 total | at most 1 | 1200 s | six fail → layout impact review |
| F3 | one V→H release diagnosis；one correction only if strict pre-release systematic offset | 16/run | 1 + conditional 1 | 1800 s/run | slip/post-release physics stops correction |
| F4 | common-X Route1；terminal non-cleanup failure may open fresh-scene Route2 | 16/route | 1/route | 1800 s/route | two fail → tray layout impact review |

F3/F4 repair success仍不授权完整 program 或 Stage 0；完整 VVHH/VHVH/VHHV、A/B/C、ABC/ACB/BAC 需要后续新证据与预算。

所有未来 GPU job 还必须满足：由 `gpu_guard.py` 原子启动；precheck≤60秒、guard PID/UUID/index 绑定；child 顶层 `receipt.json`；scene cleanup 与外层 process-group orphan 分开审计并合计；post-release 未回 baseline 即停止该卡。

F3 的 conditional correction 已有代码级硬 Gate：diagnosis execution=1；只有 `pre_release_systematic_offset` 且 grasp transform stable、EEF tracking正常时生成唯一 correction spec；correction使用 fresh scene并重查同一 current/anchor；correction execution≤1。其他分类 correction=0。
