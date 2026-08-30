# runtime-v3_3 revision-8 非正式修复与F4完整程序授权

依据用户对持续source-distinct工程修复、有限single-use验证及physical GPU0–7任一fresh-idle卡的明确授权，本轮机器白名单严格为：

```yaml
F2_diagnosis_root_per_revision: {family: F2, family_revision_index: 8}
F3_prefix_root_per_revision: {family: F3, family_revision_index: 8}
F4_block_root_per_revision: {family: F4, family_revision_index: 8}
```

- F2：一次完整root；只用一个r6/r7证据冻结的XY-only inside target0补偿，保留r6成功IK的z/quaternion；先持久化普通planner-false输入证据，无search/fallback/online adaptation。
- F3：一次完整root；contact point新增signed separation/shape identity，physical hit定义为`impulse_norm_sum>1e-10 or separation<=0`，pair presence仅audit；10mm geometry与所有动作/阈值不变。
- F4：一次完整block-root scope；先按固定顺序staged `A/B/C/AB`，全部通过后才运行full `ABC/ACB/BAC`。使用现有right arm、layout、targets、prefix、slot/final verifier，不运行strict array reorder。

所有scope single-use、finite timeout、automatic retry=false、recovery=0。GPU0–7中任一卡只有在job启动前独立fresh-idle时可用；不同卡并行必须独立UUID、namespace、lease、cache、进程树和cleanup。忙卡不得共享或干预。

Stage0、Stage1、360条formal数据、训练、H-reveal、compression与π0.5继续禁止。
