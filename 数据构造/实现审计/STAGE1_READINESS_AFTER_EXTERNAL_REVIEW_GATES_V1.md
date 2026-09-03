# Stage 1 readiness after externally reviewed recovery Gates V1

日期：2026-09-03  
统一状态：`NOT_READY_F2_MICRO_PASS_F3_GATE_FAIL_F4_REOPEN_EXHAUSTED`

## 结论

Stage 1 仍不可开始，formal accepted root/trajectory 仍为 `0/0`。本轮最有价值的进展是 F2 已把“接触前追踪崩溃”修成两个独立真实成功；但 F3 新候选仍只有一个planner survivor，F4 唯一重开在Guard schema层就终止，都没有形成development root。

| Family | 当前证据 | Development root | Stage 1 blocker |
|---|---|---:|---|
| F1 | 5 roots / 15 `r_pc` 已有 | 5 partial-development roots | 缺真实 `r_inv_path` / `r_inv_motion` 和9/9 root-atomic completion |
| F2 | top-contact micro Gate 2/2 pass；两个 `(8,0)` 左/右臂candidate的tracking/contact/25mm lift均pass | 0 new complete root | 尚未获授权生成三program的development `r_pc` root，也未补r_inv |
| F3 | 4个rotation1 tuple中仅1个A+B planner survivor；其余3个在pregrasp planner失败 | 0 | 未达至少2 survivor，所以physical=0、no-suffix未触发 |
| F4 | Run9 full-program template 3/3仍成立；Run13唯一reopen因manifest缺`asset_hashes_by_family`在child前停止 | 0 | 唯一reopen已消耗，无retry/第二replacement |

## 本轮F2/F3硬证据

- F2 planner queries=22/44，physical executions=2/4，success=2/2，GPU0 Guard terminal receipt=`496268837b0d9b7d7c6f9f51495398392eb374d33bb77f2ca17c645eb5828106`。
- F2 两次preclose position error为2.66–2.71 mm，orientation error为0.0057–0.0065 rad，均过5 mm/0.05 rad硬门；post-lift translation/orientation drift也均通过，两份raw trace与MP4已哈希封存。
- F3 planner queries=13/40；`bottle15-left-lower` Stage A 3/3与 lift-centered Stage B 7/7通过，其他三个candidate均在Stage-A pregrasp首query失败。Survivor=1<2，故physical=0、no-suffix=0；GPU1 Guard terminal receipt=`d53a8603a40f5147e1f1312dc385d5b1d5f970cbe4877a9ecfee551b3464b4cd`。
- 两job的Guard均确认child exit=0、cache removed、lease released、task-owned cleanup pass且选中GPU回到14MiB/0%/P8无compute。最终GPU0–7外部post-check无compute process。

Machine terminal：`POST_RECOVERY_F2_F3_GATE_TERMINAL_V1.json`，receipt=`32fcabf494f43b855b90f91672404a522371479c018857378ccedb58b42975df`，file SHA=`826e2f4b73fd4bde816093a0c58dcc2f910cc24738fe4f672fad52c328c441db`。

## 授权边界

Stage0不重开；Stage1、formal360、训练、H-reveal、compression、π0.5仍全部未授权。F2/F3/F4本轮已授权job已终止；任何新GPU修复、candidate、development root或r_inv均需新的明确审阅/授权。
