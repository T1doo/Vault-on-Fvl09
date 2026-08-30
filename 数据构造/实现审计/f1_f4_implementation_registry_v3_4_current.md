# F1–F4 implementation registry：runtime-v3_4 current

| Family | 当前冻结实现 | 下一Gate | accepted root |
|---|---|---|---:|
| F1 | 保留revision-2 accepted；因共享接线变化增加一次回归 | `F1_shared_regression_v3_4` | 1 |
| F2 | safety Gate→full-open→250帧→final inside Gate | `F2_inside_targeted_v10` | 0 |
| F3 | contact0/candidate0统一中段侧抓；三个pre-release上下文 | `F3_grasp_three_context_v10` | 0 |
| F4 | 四个fixed-order planner corridor→A→B/C/AB→root | `F4_corridor_A_v10` | 0 |

Phase0 active/snapshot各`449/449`，source byte-equal=`1cadd3e2…b316`。当前GPU尚未运行，accepted roots仍`1/4`，Stage0未授权。
