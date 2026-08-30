# F4 hash infrastructure v12 terminal report

## 结论

`FAILED_WITH_EVIDENCE`。这次没有证明F4 corridor可行，也没有满足Stage 0前置Gate；canonical 12-attempt manifest未生成，Stage 0保持`0/12`。

## 实际执行

- implementation：`controlled_multi_future_stage0_smoke_v1`
- source：`b312fca095687beb4c113cc59761692bef5667230ea9eb462b673b9dbcbf0d05`
- reviewed baseline commit：`324727f39632366d27639712a3ffb49f44ec70c1`
- bundle publication commit：`07c3f940b838b2809582fa4dc03ba2d0733afa9e`
- physical GPU：0，UUID=`GPU-2c620e6c-9639-2022-b573-9847dfa33769`
- actual budget：`10 planner / 0 execution / 0 recovery`
- corridor planner queries：0
- timeout：false

## 失败边界

Pristine current/anchor、canonical prefix和exact corridor contract均完成。第一个candidate `r4_successful_carry_orientation_and_corridor`保持candidate design、ordered segment IDs、right arm、layout和release semantics不变；前七个pose逐项零误差。唯一失败是terminal `A_neutral`：

```yaml
position_error_m: 0.11746700969074096
orientation_error_rad: 0.007997776852024735
allowed_position_atol_m: 0.00001
allowed_orientation_atol_rad: 0.00001
```

因此这不是raw-float噪声，Gate在第一条corridor query前正确fail closed。

## 根因边界

冻结contract在pristine scene构造；branch-neutral来自canonical common prefix的`common_center_high`。Fresh candidate先replay canonical prefix，把`common_x`移动到tray，然后重新调用common target builder。该builder根据当前`common_x`重算`common_center_high`，使terminal neutral发生宏观变化；其他A segment由未移动的A/slot推导，所以保持零误差。

Trace交叉证据：A与slot_A从首帧到末帧位置均不变；common_x移动`0.228714 m`并旋转`0.007997776852 rad`。Neutral orientation error与common_x旋转完全相同，position error接近common route midpoint对该位移的一半响应。冻结`A_neutral`等于canonical prefix的`target_neutral_pose`，不是layout文件中已被prefix repair supersede的旧`branch_neutral_pose`。

最小后续修复不是放宽容差，也不是切回旧layout neutral，而是让v12 fresh contract reconstruction只把terminal neutral override为冻结candidate/canonical replay target，并验证二者一致后重算contract hashes。前七段、layout、arm、release、program、verifier与`1e-5`容差均不动。该修复需新实现版本、CPU/static审计、source freeze和新的single-use GPU授权；本轮不自动执行。

## 安全与证据

- 三场scene cleanup全部成功；activity monitor wrappers全部恢复。
- Guard source-lock postcheck通过，timeout=false，orphan=0。
- Job cache与GPU lease均释放；GPU0 postcheck为P8/14MiB/0%且无compute process。
- Evidence：`probe_outputs/prestage0_f4_candidate_hash_infra_v12_seed20260829_run1/`
- Evidence tree：`b908a112e61058d3729db35a63a20397d1b27bebf4d93256ff8ff212eea78358`（12 files）
- Guard evidence tree：`507e0fe034c5d7d3c33cf14db7329a515050d83ed2b81a1734891d0efbd03982`（3 files）
- Guard file SHA：`ed02e117157b2fb7e94582e348d57f4b047a71f616497731e5753f1b60746081`
- Outer receipt SHA：`62f6b9b83bba15e877e0d32a828207b9028b27458f0b80b4d497cd827da2b439`
- Inner receipt SHA：`703edefffef57b96aaadc9948ad9f52f5f4fd7472added91127d2a7924162097`
- Consumption receipt file SHA：`9c76f7c8476a6bc8136602b89a2da28d5be4beb54f85376bfdfb343f441fbc1f`

Stage 1、360条formal、training、H-reveal、compression和π0.5均未运行、未授权。
