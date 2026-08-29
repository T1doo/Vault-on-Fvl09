# F2–F4 runtime-v3_3 revision-2 终止审计与后续修复 impact review

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
formal_data: false
stage0_data: false
stage0_authorized: false
review_status: evidence_sealed_repair_authorized_by_user
```

## 总结

2026-08-30，F2-r2、F3-r2、F4-r2 分别在物理 GPU4、GPU5、GPU6 上并行运行。三次运行都按 strict Gate 受控终止，没有形成 accepted root；三张卡均完成 source-lock、scene cleanup、lease/cache 清理和 orphan audit，随后回到基线状态。用户随后明确允许继续进行新的 versioned implementation repairs，不再受旧“两版”工程上限阻挡；每次 GPU 运行仍必须是单次、有限 timeout/queries/executions、无自动 retry，并保留全部失败证据。

## F2-r2

- `f2_post_settle_dynamic_pose_contract_v3` 修复有效：三个 task/physical Gate 3/3 通过。罐头从 planned `[-0.28, 0.04, 0.79]` 落稳到 `[-0.2799856067, 0.0400231481, 0.7406278253]`；XY 漂移 0.0273 mm、z 正常下落 49.372 mm、upright error `7.72e-7 rad`，50/50 帧 table contact，pose-derived linear/angular 均为 0。
- canonical prefix 1290 semantic steps、19 planner queries、1 次 reference execution，物理 Gate 通过；三次 suffix fresh replay 的 current/anchor/prefix hashes 一致。
- `inside`：`+10 cm` 成功，`+6 cm` 失败；`on` 四段全成功；`beside` 首个 preplace 失败。因此 3/3 suffix Gate 未通过，branch execution=0。
- planner=26，execution=0，recovery=0；8/8 scenes cleanup safe，orphan=0，GPU4 release verified。
- r3 impact：保持 `071_can/base1`、left arm、box2/scale0/stand3、设施布局与 verifier；inside 改为已实证可达的盒口上方 10 cm 开爪重力落盒，最终 full-OBB/contact/stability Gate不放宽；beside 恢复现有六个预注册 sector/yaw/height candidates 的固定顺序 chained preflight，首个完整通过者冻结，六个全失败则进入 layout impact review。

## F3-r2

- 初始 task/physical 3/3 通过；canonical prefix planner=20，真实 reference prefix execution=1。
- shared V Gate 仅两项失败：EEF negative amplitude=`39.618194 mm`，低于 40 mm 阈值 `0.381806 mm`；`T_eef_actor` 最大 orientation drift=`52.449613 mrad`，高于 50 mrad 阈值 `2.449613 mrad`。
- 其他核心量通过：EEF positive=`55.359960 mm`；bottle positive/negative=`55.000365/41.773438 mm`；EEF off-axis/return=`2.267766/1.587768 mm`；bottle off-axis/return=`2.689328/0.968135 mm`；bottle world orientation drift=`26.451273 mrad`；selected-gripper contact fraction=1.0，break=0。
- 直接物理证据：central 横移期间出现相对旋转；V 下行时 bottle+gripper 先接触 pad，随后接触 table，目标 EEF z=0.895 m，而实际最低约 0.908878 m。
- planner=20，branch execution=0，但 canonical reference execution=1；5/5 scenes cleanup safe，orphan=0，GPU5 release verified。
- r3 impact：保留同一 bottle/left arm、V=`±z_table 55 mm`、H=`±x_table 50 mm`、VVHH/VHVH/VHHV/shared-first-V 和全部阈值；显式冻结 r2 已选 official grasp，central z 由 held bottle+gripper envelope、support top、V amplitude 和 30 mm clearance 计算；路径改为 vertical clearance raise → same-height center carry → 50-frame neutral confirmation → shared V，carry 固定 2× time dilation。不得通过降低 40 mm/50 mrad Gate 获得成功。

## F4-r2

- common-X 9/9 planner segments、真实 reference execution、fresh replay 和全部 physical Gate 成功；common-X 位于 tray、稳定、接触连续、右夹爪打开。
- Gate-A：`A_pregrasp/A_grasp/A_lift` 成功，`A_preplace` 失败；失败 transition 为 `A_lift → A_preplace`，平移约 140.371 mm。B/C/AB 和完整 ABC/ACB/BAC 未启动。
- planner=13（common 9 + A 4），suffix execution=0，recovery=0；3/3 scenes cleanup safe，orphan=0，GPU6 release verified。
- r3 impact：保持 final layout、tray、right arm、common-X 9 段、ABC/ACB/BAC 和 verifier；对 A/B/C 统一在 lift 与 preplace 间插入一个 50% XY midpoint，不允许 A-specific fallback。每 block 由 6 段变为 7 段，staged/full 都调用同一个 target expander。

## Claim boundary

- F1 是当前唯一 accepted nonformal pre-Stage-0 root。
- F2/F3/F4 revision-2 均为终止失败证据，不能称为完整可行。
- 本轮没有 Stage 0、Stage 1、formal trajectories、训练、compression、H-reveal 或 π0.5。
- 用户允许继续 versioned repair，不等于允许自动 planner retry、覆盖失败、放宽 verifier 或启动 Stage 0。

## 不可变证据

| Family | Namespace manifest | Tree SHA-256 | Root/staged receipt SHA-256 | Guard SHA-256 |
|---|---:|---:|---:|---:|
| F2 | `F2_ROOT_RUNTIME_V3_3_REVISION2_FAILURE_EVIDENCE_MANIFEST_20260830.json` | `8e735bb894c1da4a2825933097a60350c603962bdd27b8e24a6223bae900203e` | `90f10ab92c534b409e9755934820318e996f212c4c1ac116a01f47417a9a75f2` | `4395def1668369b00e52b50c59bc012dfdfbe47aa0fc3c43008777bd06ff2d28` |
| F3 | `F3_ROOT_RUNTIME_V3_3_REVISION2_FAILURE_EVIDENCE_MANIFEST_20260830.json` | `9d6e711f5f02fe9372cfb4d14e495bff74d20e6d38bff3b51643d9fdbb74dced` | `74ee01a129bbc3c4b32497f49e805f50856f1a2edc8ca3689065bef37f8d910c` | `4f5df4f0a44b76b061e51cd84ec4ada3c357f621afe8a7b0ff79c3d3584e94e0` |
| F4 | `F4_ROOT_RUNTIME_V3_3_REVISION2_FAILURE_EVIDENCE_MANIFEST_20260830.json` | `effc52ce16925787710652b77a54ee7671718b7df6bb4db6078614cc92230ebf` | `06c13c8f05dc6a6dc65b3d1b84ea8f280d291715c912250a431e37612ac420fc` | `bea17f06ccc44ea66b793b4ee01ae266d73b6be2246f12f0f462ce1c7370b527` |

