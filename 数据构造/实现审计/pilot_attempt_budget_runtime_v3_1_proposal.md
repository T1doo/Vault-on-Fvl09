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
