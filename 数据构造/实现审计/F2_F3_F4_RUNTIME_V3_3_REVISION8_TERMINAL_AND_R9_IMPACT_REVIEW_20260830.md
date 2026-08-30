# runtime-v3_3 revision-8 终止审计与 revision-9 impact review

## 裁决

`BLOCKED_WITH_REASONS`。Revision-8 的三个一次性非正式 scope 已全部终止并保留失败证据；F1 仍是唯一完整 accepted nonformal root。F2 的 `on`、`beside` 真实通过，但 `inside` 在开夹释放时被高速带出盒腔；F3 的三个程序全部完成真实 V/H 和回垫动作，但只有 `VHVH` 通过最终等价，root 为 `1/3`；F4 在 A 的 staged preflight 因 NumPy 数组 JSON 序列化缺陷停止，尚未执行任何 block。

## F2：目标位置已改善，当前 blocker 是开夹释放动力学

- Root 计数为 `32 planner / 3 execution / 0 recovery`；`on` 与 `beside` accepted，`inside` failed verifier。
- XY-only compensation 生效。开夹前 actor 位置误差约 `2.674 mm`；原有 10+50 帧 settle Gate、finger contact、identity、无非预期设施碰撞与 `24.203 mm` rim clearance 全部通过。
- 开夹后 selected fingers 仍接触罐头 `157` 帧；脱离前一帧速度向量约 `[-0.2106, -0.0144, -1.1222] m/s`，总线速度 `1.1419 m/s`、角速度 `5.1597 rad/s`。开夹后的峰值达到 `1.4897 m/s` 与 `14.7755 rad/s`。
- 接触期间 actor 位移约 `[-25.607, -1.949, -72.301] mm`，随后与盒体形成 47 个 contact records 并静止在 true cavity OBB 之外。失败不是 verifier 边缘误差，也不是继续改 XY target 可以解决的问题。
- Revision-9 只允许研究固定的 two-stage balanced-preload release：先补 actual finger effort/drive gain/target-error 与精确 open/disconnect marker，再用单一预注册 partial-open hold + fail-closed geometry/support/disengagement Gate + full-open。不得换罐头、换手臂、换盒子或搜索多个 release 参数。

## F3：V/H 与物理接触信号成立，回垫后的滚转仍不稳定

- Root 计数为 `96 planner / 3 execution / 0 recovery`；三个 suffix preflight、全部 V/H realized-motion、selected-gripper contact continuity、free-space contact 和真实 shape identity/signed separation 信号均通过。
- Program 终态：`VVHH=failed_verifier`、`VHVH=accepted`、`VHHV=failed_verifier`，因此完整 F3 root 为 `1/3`，不能接受。
- 开夹前位置误差分别为 `1.959 / 2.164 / 2.146 mm`，姿态误差为 `25.287 / 41.361 / 41.409 mrad`；EEF tracking 正常，grasp transform 在 frozen tolerance 内稳定。
- 最终 after-rest 误差分别为：

| Program | position | orientation | footprint/support/stable |
|---|---:|---:|---|
| VVHH | 12.624 mm | 256.921 mrad | pass |
| VHVH | 3.295 mm | 16.407 mrad | pass |
| VHHV | 9.828 mm | 190.866 mrad | pass |

- `VHVH` 在开夹前姿态误差反而不小于两条失败分支，却最终回稳；因此当前自动 diagnosis 将所有三条都标成 `pre_release_systematic_offset` 并允许 correction 的结论过强，不能据此套一个全局 actor→EEF correction。Revision-9 必须先修 correction Gate：accepted/final-equivalent branch 不得请求 correction，并把 transient roll 与 final failure 分账。
- 下一安全方向是 `f3_post_release_roll_impact_review_v9`：保持瓶子、pad、左臂、V/H 轴和三个程序不变，先审计开夹期间真实 finger effort/drive、接触断开与角动量；只允许一个预注册的 controller-only symmetric staged release 假设。若需要改 pad、初始姿态、摩擦或物理属性，必须另做 impact review 并取得用户批准。

## F4：本轮是 0-execution 软件缺陷，不是物理失败

- Scope 计数为 `10 planner / 0 execution / 0 recovery`。
- Fresh pristine current/anchor、common-X prefix reference 和 prefix artifact 已生成；A staged preflight 随后在 `f4_top_down_block_carry_v8._json_clone()` 处报 `TypeError: Object of type ndarray is not JSON serializable`。
- 错误发生在 target contract 构造阶段；A/B/C/AB 均未执行，完整 `ABC/ACB/BAC` 正确地没有启动。所有 scene cleanup、source lock、lease/cache/orphan/GPU release audit 通过。
- Revision-9 仅修 additive JSON canonicalization，使 `numpy.ndarray` 与 `numpy.generic` 转为 JSON-safe primitives，并增加真实 staged callback 形状的 CPU regression。不得借机修改 layout、tray、right arm、role-slot mapping、top-down target、neutral pose、program 或 verifier。

## Evidence trees

| Family | Files | Tree SHA-256 |
|---|---:|---|
| F2 | 48 | `767ded27e13a3e691220c5d1ce0b34ba1f98faae75e7978d9187703aba4a0ccb` |
| F3 | 48 | `e4e88965529e1678ac4aba47fd33bcb693f456c77ab64c10e5b5e5c56fb67455` |
| F4 | 11 | `09bc9b374d6001fff82292b17da053a055db4f6c2ee6c5a6736e395af97f08cb` |

F3 有 7 个单文件超过 GitHub 100 MB（3 个 branch trace、3 个 raw NPZ 与 root receipt）。它们保留在服务器原 namespace，字节数与 SHA-256 全部记录在 immutable evidence manifest；GitHub 审阅快照只上传其余可接受大小的 receipts/artifacts 和完整 manifest，不会修改、截断或伪装大文件。

三个 Guard 均无 timeout，post source lock 通过，scene/cache/lease cleanup 通过，task-owned orphan 为 0，GPU0 返回 14 MiB 基线。Stage 0、Stage 1、formal trajectories、训练、compression 与 π0.5 仍为 0/未授权。
