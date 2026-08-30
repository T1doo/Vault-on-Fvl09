# runtime-v3_3 revision-9 非正式 source-distinct 修复授权

依据用户在当前持续目标中对“找出原因、不断做source-distinct修正并推进到Stage0前”的明确授权，以及当前fvl05共享规则对RoboTwin受控数据构造仅使用physical GPU0的限制，本轮机器白名单严格为：

```yaml
F2_diagnosis_root_per_revision: {family: F2, family_revision_index: 9}
F3_prefix_root_per_revision: {family: F3, family_revision_index: 9}
F4_block_root_per_revision: {family: F4, family_revision_index: 9}
```

- F2：同一`071_can/base1`、left arm、box/scale/stand与三个relation不变；只测试一个R8证据驱动的balanced-preload partial-open，必须在true-inside、stable、physical box support与selected-finger disengagement全部通过后才full-open。无target/asset/layout/search/fallback变化。
- F3：同一`001_bottle/base13`、left arm、pad、table-z/table-x与`VVHH/VHVH/VHHV`不变；只测试一个balanced-preload后固定`+0.16` normalized slow-disengagement控制。必须在原final position/orientation、footprint、pad support、stable与assembly disengagement全部通过后才full-open；不改transform、pad、物理属性或verifier阈值。
- F4：只修真实callback ndarray的JSON-safe canonicalization，并继续固定staged `A/B/C/AB`→full `ABC/ACB/BAC`。不改right arm、layout、tray、target、neutral、program或verifier。

所有scope single-use、finite timeout、automatic retry=false、recovery=0。只允许physical GPU0在启动前独立fresh-idle时运行；不得共享忙卡或干预其他用户进程。

Stage0、Stage1、360条formal数据、训练、H-reveal、compression与π0.5继续禁止。
