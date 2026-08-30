# F1–F4 implementation registry：runtime-v3_3 revision-7 terminal current

```yaml
accepted_nonformal_roots: 1/4
F4_A_micro_gate: accepted
stage0_authorized: false
new_gpu_launch_authorized: false
```

| Family | revision-7真实结果 | 计数 planner/execution/recovery | 下一步 |
|---|---|---:|---|
| F1 | revision-2 root accepted | 46/3/0 historical | 无 |
| F2 | inside compensated首endpoint `IK_FAIL`；on/beside只规划通过 | 30/0/0 | fixed XY-only compensation + planner-false evidence |
| F3 | 三program全部V/H与10mm geometry通过；zero-impulse pair造成preopen false negative | 96/3/0 | signed separation/shape + physical contact classifier |
| F4 | A-only micro accepted；rise=17.2152mm、contact/noninterference全部通过 | 13/1/0 | staged A/B/C/AB与完整ABC/ACB/BAC |

F4 micro不是完整root，accepted roots仍1/4。完整审计见`F2_F3_RUNTIME_V3_3_REVISION7_TERMINAL_F4_MICRO_ACCEPTED_AND_R8_IMPACT_REVIEW_20260830.*`。
