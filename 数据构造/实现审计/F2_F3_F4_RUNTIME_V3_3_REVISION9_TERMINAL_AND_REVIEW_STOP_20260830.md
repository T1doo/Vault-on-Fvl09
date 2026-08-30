# runtime-v3_3 revision-9 终止审计与审阅停止点

## 裁决

`BLOCKED_WITH_REASONS`。按用户要求，revision-9 三项终止后停止继续修复，等待 GPT 审阅方向。F1 revision-2 仍是唯一完整 accepted nonformal root；F4 revision-7 A-only micro仍只是accepted nonroot Gate。Stage0明确未授权。

## F2：释放冲击显著下降，但50帧Gate时仍未inside/stable

- Root=`failed_verifier`，计数=`32 planner / 3 execution / 0 recovery`。
- `on=accepted`、`beside=accepted`；`inside=failed_execution`，错误为`F2 balanced-preload release Gate blocked full-open`。失败保留partial trace，未执行后续full-open。
- Balanced target由实际双指qpos `[0.0235749, 0.0215057] m`的均值得到，normalized target=`0.5916414`。双指在最终10帧已无physical pair，盒体physical support连续成立。
- 相比revision-8，开夹后的峰值从约`1.4897 m/s / 14.7755 rad/s`降到`0.01660 m/s / 0.72399 rad/s`，说明减小preload方向有真实效果。
- Gate仍失败于：`true_cavity_obb=false`、`stable_angular_window=false`；linear stable、finger disengagement、box support均pass。Gate只在partial-open结束后额外等待50帧（0.2s），此时罐头仍在滚动/沉降。
- 当前证据不能自动裁决下一步是仅延长固定settle window、改变partial release aperture，还是几何目标仍需调整；不得在GPT审阅前进入revision-10。

## F3：revision-9 release未被测试，真正上游 blocker 是抓取姿态漂移

- Root=`failed_verifier`，计数=`96 planner / 3 execution / 0 recovery`。
- 三条suffix preflight均通过；三条真实分支均在原`contact-free pre-open Gate`失败，revision-9 staged release evidence全部为null，没有执行任何partial/full open。
- 三条的position/orientation与grasp drift：

| Program | bottle pos | bottle orientation | grasp translation | grasp orientation |
|---|---:|---:|---:|---:|
| VVHH | 3.397 mm | 51.133 mrad | 3.481 mm | 52.386 mrad |
| VHVH | 10.076 mm | 127.853 mrad | 10.006 mm | 134.190 mrad |
| VHHV | 3.162 mm | 79.094 mrad | 3.155 mm | 84.855 mrad |

- EEF position/orientation、瓶子/EEF速度、contact continuity、actor identity、free-space physical contact均pass。第一条suffix event的瓶子orientation drift分别为`56.829 / 53.807 / 53.462 mrad`，而contact fraction均1.0、break=0；说明“仍接触”不等于瓶子在夹爪内姿态不滑移。
- Revision-8同一root曾完成三条release并有1/3 accepted，revision-9相同科学设计/seed却在pre-open显著漂移，暴露的是realized grasp robustness/determinism问题，而不是staged-release公式本身。
- GPT应先裁决抓取稳定、grasp transform verifier、事件幅度/控制与可重复性，再决定是否值得继续测试release。

## F4：JSON缺陷已修，真实A_carry_mid IK成为终止 blocker

- Scope=`failed_f4_staged_block_gate`，计数=`14 planner / 0 execution / 0 recovery`。
- Fresh current/anchor、common-X prefix与prefix artifact通过；revision-8的`ndarray is not JSON serializable`不再出现。
- A staged preflight：`A_pregrasp/A_grasp/A_lift`均CuRobo success；`A_carry_mid`以`MotionGenStatus.IK_FAIL`失败（10 attempts），所以A未执行，B/C/AB与ABC/ACB/BAC按合同未启动。
- 失败goal约为`[0.1550, 0.0780, 0.9994, q...]`；CPU nominal noninterference虽然pass，但不能替代真实IK/workspace证据。
- GPT应审查carry-mid构造、右臂工作区/姿态、是否应先分段或使用已证明的neutral carry，及任何layout改变是否需要impact review。

## 安全与证据

- 三个Guard均无timeout、post-source-lock pass、所有scene/cache/lease cleanup通过、task-owned orphan=0，GPU0均返回14 MiB/0%/无compute。
- Evidence trees：

| Family | Files | Tree SHA-256 |
|---|---:|---|
| F2 | 45 | `8c6e3ded14b011d4312d9db637c9df8e98cce05a91b9d777423f8f17a7663332` |
| F3 | 39 | `3037c0a3435b3e9bd1053b2ebf46524b2873857b3b6378e511d0c84380f3e1ca` |
| F4 | 11 | `120bd5579029a7f7a82051babd3b14136fa391d63fdf9ad4ce7cb5135f7f8f33` |

- F3四个超过GitHub 100MB的文件保留服务器byte-identical，bytes/SHA记录在manifest与`REVISION9_GITHUB_SNAPSHOT_BOUNDARY_20260830.json`；GitHub包含其余receipts/artifacts。
- 没有Stage0、Stage1、360条formal数据、训练、H-reveal、compression或π0.5。
