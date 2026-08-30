# runtime-v3_3 revision-6 非正式修复授权

依据用户当前线程中对持续source-distinct工程修复的明确授权，本轮机器白名单严格为：

```yaml
F2_diagnosis_root_per_revision: {family: F2, family_revision_index: 6}
F3_prefix_root_per_revision: {family: F3, family_revision_index: 6}
F4_micro_lift_diagnosis_per_revision: {family: F4, family_revision_index: 6}
```

- F2：一次完整root；仅增加10帧pre-release warmup，随后原final50阈值与完整60帧安全Gate。
- F3：一次完整root；center-aware bottle+assembly compound envelope冻结10mm release geometry clearance。
- F4：一次A-only micro diagnosis；A/B/C统一top-down pregrasp/grasp +16mm，micro仍+20mm，不运行B/C/full root。

所有scope single-use、finite timeout、automatic retry=false、recovery=0。允许physical GPU0–7中任一fresh-idle卡，但若当前执行环境施加更窄GPU规则，以更窄规则为准。F1、F4 full/IK/prefix smoke和其他revision均不授权。

Stage0、Stage1、360条formal数据、训练、H-reveal、compression与π0.5继续禁止。
