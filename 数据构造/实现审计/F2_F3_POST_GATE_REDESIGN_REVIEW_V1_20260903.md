# F2/F3 post-Gate redesign review V1

日期：2026-09-03  
状态：`CPU_REDESIGN_IMPLEMENTED_AWAITING_EXTERNAL_REVIEW_AND_NEW_GPU_AUTHORIZATION`

本审查只使用已经封存的 Run3 F2 raw trace 与 Run6 F3 planner evidence。没有重跑 F2/F3、没有启动 GPU，也没有改变科学 family contract、formal denominator 或 verifier threshold。

## F2：失败发生在接触前，不是抓稳后滑落

两次真实 F2 physical 的罐子从头到尾没有移动，selected-gripper contact frame 都为0。机械臂虽收到 planner-success control，但在接近目标后发生大幅跟踪失真：

| Candidate | pregrasp位置/姿态误差 | grasp位置/姿态误差 | 最大关节跟踪L2 | EEF距罐中心最近 |
|---|---:|---:|---:|---:|
| can0+box2-left | 211.9 mm / 0.7828 rad | 196.6 mm / 0.5667 rad | 0.5301 rad | 250.4 mm |
| can5+box8-left | 140.0 mm / 0.5373 rad | 142.7 mm / 0.4081 rad | 0.5700 rad | 247.1 mm |

所以原标签 `PRE_LIFT_GRASP_NOT_ACQUIRED` 没错，但更精确的根因是 `PRECONTACT_ARM_TRACKING_FAILURE`：夹爪根本没有到达冻结 grasp pose，随后闭合只是空夹。盒口仍分别有约29.8 mm/52.5 mm水平余量，不能继续用“换大盒子”解释。

新增 `f2_precontact_tracking_recovery_v1.py`：

- 在 close 之前分别要求 pregrasp/grasp tracking ≤5 mm、≤0.05 rad；
- tracking 未过立即停止，不再浪费 close/lift/insertion；
- 下一 candidate policy 保持 can0+box2、can5+box8 × left/right，改为 planner-assisted official grasp candidates 后冻结一个 exact pose，不再固定失败的 side-contact rotation0；
- 只有 tracking、contact identity/continuity、25 mm lift 全过后才允许 insertion；
- future Gate仍最多4个candidate、每项一次、两次同类失败即停、至少2个不同成功才freeze；
- 新GPU Gate尚未授权。

Contract SHA：`1b1edd046e4c9e58c0490d129967219657403d5f79cae509bba633396829129d`。

## F3：固定全局 central 制造了不必要的137 mm跳转

Run6 中 bottle15-left-lower 的 Stage A 三段全部 planner pass。Stage A lift pose为约 `[-0.0569, 0.0535, 0.8799]`，但旧 Stage B 强制先去全局 `[0, -0.05, 0.95]`，首段距离137.3 mm，并在10次尝试后报 `FINETUNE_TRAJOPT_FAIL`。

F3冻结科学定义只要求 table-frame的 `V=±z`、`H=±x`、等端点和shared-first-V，并不要求固定全局中心。因此新增 `f3_lift_anchored_event_center_v1.py`：

- central精确等于 Stage A lift pose，首段位移从137.3 mm降为0；
- 保持 V幅度±55 mm、H幅度±50 mm；
- 保持全部orientation、事件顺序、table-frame轴和最终central不变；
- pure target audit已证明 first=lift、三个central相等、V只改z、H只改x；
- 当前四个strata是终端证据，禁止直接重跑；新的candidate universe仍需外部审查并先freeze；
- 至少2个不同physical candidate通过前，不运行same-prefix×3 no-suffix diagnostic。

Target audit SHA：`d42e9db609b52e8c0344015cd87c9e6cc9e52df8d524134a26f861243880c17a`。Contract SHA：`e12a9165f6a952248f723376a57df9d1f56866f2c498569e65fa5e0a4dcac3ba`。

## 边界

- F4保持 template 3/3 pass、development root final incomplete/no replacement；
- Stage0不重开；
- Stage1、formal360、训练、H-reveal、compression、π0.5继续禁止；
- 本次source状态仅为 `implemented_cpu_validated`，不是planner/physical/scientific pass。

Machine artifact：`F2_F3_POST_GATE_REDESIGN_REVIEW_V1_20260903.json`，payload `5abdf436ed092bc9c761869615b6f93cd834864d641298e7ba8e87ddaaf7a3d5`。
