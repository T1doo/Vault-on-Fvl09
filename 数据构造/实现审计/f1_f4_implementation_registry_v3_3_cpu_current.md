# F1–F4 implementation registry：runtime-v3_3 revision-8 CPU current

| Family | revision-8实现 | Envelope | 状态 |
|---|---|---:|---|
| F1 | revision-2 root保持accepted | 46/3/0 historical | `accepted_nonformal_root` |
| F2 | fixed XY-only inside target0；planner-false仍保存完整输入 | 32/3/0 | `r8_cpu_ready_not_run` |
| F3 | separation/shape/impulse physical signal贯穿preopen→release→+250 | 96/3/0 | `r8_cpu_ready_not_run` |
| F4 | top-down七段staged A/B/C/AB；通过后full ABC/ACB/BAC | 118/7/0 | `r8_full_cpu_ready_not_run` |

F4 A-only micro为accepted nonroot Gate；完整roots仍1/4。Active/snapshot各412/412、diff零；source=`4b5ac619c0d765024bc7cdc01ea02e2a30e7a9bc195274961c626aa48f0c2d21`，budget=`bd62453d41b214a54eea045a9b9d6f641c8802cf2f384143a9e7b71d7e61b14a`。F2/F3 full与F4 block-root exact bundles已发布、尚未消费。
