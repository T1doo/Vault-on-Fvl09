# runtime-v3_3 revision-9 CPU baseline

Revision-9 严格依据 revision-8 terminal evidence，科学设计、对象、执行臂、layout、candidate programs 与 verifier 阈值均未改变。

- F2：保留 revision-8 的 fixed XY target、同一 `071_can/base1`/left arm/box-scale-stand。先记录实际 qpos/qvel、applied qf、drive target/velocity error、stiffness/damping/limit/mode及force-mode controller effort estimate；只执行一个 mean-aperture balanced-preload partial-open。只有 true cavity OBB、50帧stable、10帧physical box support与finger disengagement全部通过才允许原full-open。
- F3：保留 `001_bottle/base13`、left arm、pad、table-z/table-x和`VVHH/VHVH/VHHV`。Diagnosis先判final equivalence，已accepted分支不再错误请求correction。Release只允许mean-aperture balance后固定`+0.16` normalized的慢速disengagement；只有原position/orientation、footprint、pad support、stable与assembly disengagement全部通过才full-open。
- F4：只增加NumPy ndarray/scalar到JSON primitive的canonicalization；真实staged callback shape与list输入生成逐字段相同receipt。Top-down targets、right arm、layout、neutral、A/B/C/AB、ABC/ACB/BAC和verifier不变。
- Raw：primary 26-D/250 Hz/N+1合同不变。新增audit-only gripper qvel、applied qf、position/velocity error、drive properties/mode和controller effort estimate。`get_qf`明确不是actuator/contact effort，estimate明确不是measured force。

```text
active tests = 427/427
snapshot tests = 427/427
active/snapshot diff = zero
official tracked commit = c3ddfa8b97d5519efa828b075999bd0006778e5e
source = f76c013aebbe98d705dc62f77a83c47fdefbc899d0818e84b489639b1cd95d21
budget = 56b5d18115e5c0f7d24738ab49909633f26a69fd8e4b2b6235952f1c4751687f
parent = f8c7027161480fcfca08da11154e3eecd2fa398672c0a079fff55de6f98cbc8e
```

当前仅允许clean publication；revision-9 ledgers、bundles与GPU outputs均不存在。发布并恢复clean HEAD后才能签发F2/F3/F4三个single-use非正式scope。Stage0继续禁止。
