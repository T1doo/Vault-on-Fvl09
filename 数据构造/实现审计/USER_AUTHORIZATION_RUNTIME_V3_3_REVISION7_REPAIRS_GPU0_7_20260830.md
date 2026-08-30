# runtime-v3_3 revision-7 非正式修复授权

依据用户当前线程对持续source-distinct工程修复、有限单次GPU验证以及physical GPU0–7任一fresh-idle卡的明确授权，本轮机器白名单严格为：

```yaml
F2_diagnosis_root_per_revision: {family: F2, family_revision_index: 7}
F3_prefix_root_per_revision: {family: F3, family_revision_index: 7}
F4_micro_lift_diagnosis_per_revision: {family: F4, family_revision_index: 7}
```

- F2：一次完整root；只改变`inside`第一个EEF command，补偿严格绑定r6 immutable evidence；desired actor target、retreat、rest、on、beside、box/layout和final verifier不变，alignment仅作诊断，不新增科学阈值。
- F3：一次完整root；只修projection consumer旧字段、planner前partial evidence和implementation-error分类；V/H、三program、bottle、arm、layout、10mm clearance与verifier不变。
- F4：一次A-only micro diagnosis；只修role-A trace provenance与既有`1e-10` nonzero-impulse接触语义；+16mm targets、20mm micro、prefix、layout、arm和所有数值Gate不变，不运行B/C/full root。

所有scope single-use、finite timeout、automatic retry=false、recovery=0。physical GPU0–7中任一张卡只有在该job启动前独立fresh-idle时才可使用；不同卡可并行，但必须独立UUID、namespace、lease、cache、进程树和cleanup。忙卡不得共享，也不得干预其他用户进程。

Stage0、Stage1、360条formal数据、训练、H-reveal、compression与π0.5继续禁止。
