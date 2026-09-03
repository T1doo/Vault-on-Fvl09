# Stage 1 readiness after production micro Gate V1

日期：2026-09-03

结论：`NOT_READY_F2_F3_TEMPLATE_BLOCKED_F4_DEVELOPMENT_ROOT_PENDING`。

Stage 0 继续保持 `STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`，没有重开或覆盖。正式 accepted roots/trajectories 仍为 `0/0`，Stage 1、formal 360、训练、H-reveal、compression、π0.5 均未授权。

## 统一状态

| Family | CPU contract | 真实物理/程序证据 | Development r_pc | 当前裁决 |
|---|---:|---|---:|---|
| F1 | pass | 历史 5 roots / 15 r_pc 全通过 | 5 roots / 15 trajectories | 模板和 r_pc 已有；Stage 1 前仍缺 real r_inv_path、r_inv_motion 与 root-atomic 9/9 |
| F2 | pass | 2 次真实抓持，连续同类 `PRE_LIFT_GRASP_NOT_ACQUIRED`，0 success | 0 | 需要 asset/grasp-pose/gripper redesign；不是盒子/插入调参问题 |
| F3 | pass | 姿态哈希已修复；7 planner queries，0 physical；1 个候选 Stage A 过但 Stage B 首段失败，其余 3 个 Stage A 首段失败 | 0 | 需要 candidate/layout/grasp-corridor planner-solvability impact review；禁止盲目换 seed |
| F4 | pass | source planner 3/3、isolation 5/5、真实完整 ABC/ACB/BAC 3/3、same-current/anchor/final-state-equivalence 全过 | 0 | full-program template qualified；下一步最多一个 development r_pc root |

## F4 新增可信证据

Run 9 在同一 r01 上真实执行了 `ABC → ACB → BAC`，每条各一次、各 42 planner queries，三条全部通过 A/B/C slot、common-X preservation、gripper-open 与 neutral checks。三分支 current 和 anchor 哈希分别完全一致；最终状态最大位置/姿态差为 1.291 mm / 0.012804 rad，低于冻结的 30 mm / 0.20 rad 门限。

这证明 F4 当前模板能完整执行三种顺序，但 Run 9 是 bounded qualification bundle，不是 accepted development root：尚未按 root-once/reference-only 方式封装 current，且缺 root finalizer、failure/orphan/balance/leakage receipts。

## 下一执行顺序

1. F4：只执行最多一个 development `r_pc` root。
2. F2：基于两次真实抓持失败做 versioned asset/grasp-pose/gripper redesign impact review，再申请/签发新的 bounded micro Gate。
3. F3：基于 planner evidence 做 versioned candidate/layout/grasp-corridor redesign impact review，再申请/签发新的 bounded Gate；当前不允许 no-suffix diagnostic。
4. 各 family 拥有 development r_pc root 后，实现 real `r_inv_path`、`r_inv_motion`、root-atomic 9/9 finalizer 和完整审计，再重新申请 Stage 1。

Machine artifact：`STAGE1_READINESS_AFTER_PRODUCTION_MICRO_GATE_V1.json`，payload `9f03f2a0fa7faff58fcd9f52a48c45a644e55680a7667ec39db2333224cf29c3`。
