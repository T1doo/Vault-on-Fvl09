# runtime-v3 finite probe budget proposal

```text
status = proposed_for_user_review
approved = false
frozen = false
gpu_probe_authorized = false
stage0_authorized = false
```

| Family | execution | planner | timeout | 停止线 |
| --- | ---: | ---: | ---: | --- |
| F1 | red/green/blue 各 1 | 12/branch | 1200 s/branch | 三条按固定顺序都运行；不足 3/3 pass 则 incomplete |
| F2 | 最多 1 | 16 total；最多 6 candidates | 1200 s | 6 个全失败进入 stand-layout impact review |
| F3 | 1 诊断；仅 pre-release offset 时再 1 correction | 16/run | 1800 s/run | post-release drift 立即进入 physics impact review |
| F4 | 最多 2 个固定 route，各 1 | 16/route | 1800 s/route | 两 route 全失败进入 tray-layout impact review |

Recovery=0，禁止自动 retry。真实 root integration 的预算要等四个 family repair Gates 后再提，不在本 proposal 中猜测。
