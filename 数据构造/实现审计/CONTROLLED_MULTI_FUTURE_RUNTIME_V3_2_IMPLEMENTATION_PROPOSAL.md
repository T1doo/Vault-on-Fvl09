# Controlled Multi-Future runtime-v3_2 implementation proposal

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_2
implementation_revision: runtime_v3_2_common_hardening_v1
formal_data: false
stage0_data: false
stage0_authorized: false
```

## 公共修复

- Root新增`root_events.jsonl` append-only账本；final root receipt写入失败时返回`failed_final_receipt_serialization`并保留cleanup/planner/branch证据；
- 新增统一`planner_dtype_v3_2`：planner qpos/goal/trajectory position/velocity为float32，geometry/verifier为float64；
- 新增request-bound v3_2 authorization、scope budget、guard v2.3和family entry；
- 所有旧v3_1 evidence/authorization保持不可变、不可重放。

## Family新路线

- F1：不改scene/program，以统一dtype重新执行red→green→blue；最多1个新repair；
- F2：GPU前冻结官方object×plasticbox compatibility matrix；
- F3：先执行actual post-grasp qpos驱动的4cm/full lift专项诊断；
- F4：优先right-arm mirror，联合审计arm×tray model×完整layout。

只有4个accepted nonformal roots后才允许生成但不执行Stage0 package。

CPU current：active/snapshot 176/176 tests passed，append-only故障注入与非零dtype测试通过。
