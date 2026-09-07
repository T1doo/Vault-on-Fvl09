# Pilot48登记一致性检查

只读检查`pilot_cells.json`的48个固定格子、A/path与B/motion映射、重复轨迹身份、每个pilot组的root/current/candidate一致性，以及已登记验收字段的完整性。接受状态支持现有`accepted_existing`和未来明确登记的`accepted_new`；pending格子不得填写伪造成功证据。不会写登记表。

这是**登记结构一致性**，不是重新读取raw/视频的验收，也不能证明物理成功、无泄漏、连续六条采集、完整Stage1或整个Goal完成。`pass=true`只表示登记内部无冲突；`registration_matrix_full`单独表示是否48格全部登记。

2026-09-07主线程验证：当前18格登记一致，完整pilot组为F1/A、F1/B、F4/A。F4正在运行的数据没有提前纳入。重复cell、重复raw、混合current、失败current审计和虚报数量等CPU反例均拒绝。

运行：在workspace Python环境设置`PYTHONDONTWRITEBYTECODE=1`和audit目录`PYTHONPATH`后，执行`python -m goal_pilot48_v1.pilot_matrix_audit_v1.audit`。这里只用stdlib，不初始化GPU或模拟器。
