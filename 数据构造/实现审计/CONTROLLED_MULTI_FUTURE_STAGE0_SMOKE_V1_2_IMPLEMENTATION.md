# Controlled Multi-Future Stage 0 smoke v1.2 — F2 replacement CPU freeze

## 范围

本版只修复Stage 0 v1.1中F2 planned root spec遗漏冻结`scene_layout`的基础设施接线错误。它不重新运行F1，不修改F3/F4 Stage 0证据，也不改变F2物体、程序、seed、arm、关系语义或verifier。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_stage0_smoke_v1_2
scope: Stage0_v1_2_F2_root_A_scene_layout_replacement
replacement_attempts: 3
automatic_retry: false
recovery_attempts: 0
stage0_authorized: true
stage1_authorized: false
formal_data: false
```

## Frozen F2 binding

`F2FrozenSceneLayoutBindingV1`绑定此前runtime-v3_4_1已使用的intended layout v2：

- `071_can/base1`，left arm；
- `062_plasticbox/base2`；
- `072_electronicscale/base0`；
- `074_displaystand/base3`；
- seed=`20260829`；
- programs=`F2-inside / F2-on / F2-beside`。

Spec同时携带role-explicit poses、legacy runner fields、object modelnames/IDs、layout payload hash和binding hash。Family runner只从完整layout中提取冻结legacy core，不再要求整个扩展payload与旧六字段JSON字节相同。

原v1.1 F2 scene因layout字段缺失使用了scene class default位置，其current/anchor不等于intended layout；本版明确记录`not_comparable_due_to_missing_layout_binding_and_default_layout_drift`，不伪造same-current。Replacement会与同seed、同layout、同物体/arm的runtime-v3_4_1 intended reference做RGB/state/anchor lineage复核。

## Replacement与seal

三个新attempt逐一绑定旧slot：

```text
stage0-v1_2-F2-rootA-01 -> stage0-v1_1-F2-rootA-01
stage0-v1_2-F2-rootA-02 -> stage0-v1_1-F2-rootA-02
stage0-v1_2-F2-rootA-03 -> stage0-v1_1-F2-rootA-03
```

旧attempt/receipt不删除、不覆盖。Replacement-aware finalizer使用：F1原3条 + F2新3条 + F3原3条 + F4原3条，active slots仍为12；历史terminal receipts为15。只要active 12 slots均有非infrastructure可信终态，就可封存为`STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`，不要求12/12成功。

## CPU验证

```text
focused replacement tests: 10/10 passed
active full suite: 530/530 passed
snapshot full suite: 530/530 passed
source Python files: 190
test Python files: 94
compile: passed
active/snapshot: byte-equal
source SHA-256: e854fd9b35f01ef1eee1724c73d47e9ce750051650559c1b077e7739a1f5f351
tests SHA-256: 9bb336ace6d8749cddaa25a72f2a681701eadb31fb8915d1502486d9103a8a76
```

下一步：发布本CPU freeze；从clean published HEAD签发唯一F2 replacement bundle；在任一fresh-idle GPU0–7运行一次完整F2 root（3 programs，各1次，无retry），随后运行v1.2 finalizer。不得在结果出来后现场热修。
