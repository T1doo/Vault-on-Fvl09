# F1–F4 implementation registry：runtime-v3_3 revision-8 terminal current

| Family | revision-8实现 | Envelope | 状态 |
|---|---|---:|---|
| F1 | revision-2 root保持accepted | 46/3/0 historical | `accepted_nonformal_root` |
| F2 | fixed XY-only inside target0；planner-false保存完整输入 | 32/3/0 actual | `on+beside accepted; inside release dynamics failed` |
| F3 | separation/shape/impulse physical signal贯穿preopen→release→+250 | 96/3/0 actual | `VHVH accepted; VVHH/VHHV failed; root 1/3` |
| F4 | top-down七段staged A/B/C/AB；通过后full ABC/ACB/BAC | 10/0/0 actual | `A preflight ndarray serialization failure` |

F4 A-only micro仍是accepted nonroot Gate；完整roots仍1/4。Revision-8 exact bundles已全部消费且终止，三个Guard均cleanup/source/GPU safe。Source=`4b5ac619c0d765024bc7cdc01ea02e2a30e7a9bc195274961c626aa48f0c2d21`，budget=`bd62453d41b214a54eea045a9b9d6f641c8802cf2f384143a9e7b71d7e61b14a`。下一步必须使用新的revision-9 source/hash/budget/namespace；Stage0仍禁止。
