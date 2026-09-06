# 单一路径修订 V3：已成功低 pregrasp → 高 pregrasp

旧 runtime_v2、height recipe、003失败不改。新 `micro.py` 从v2隔离复制，仅增加 `route_pregrasp`、四次query上限、读取 `manifest.route_spec_path`；仍由 `manifest.recipe_spec_path` 读取同一height revision2，grasp/close/hold/lift/Gates不改。

精确顺序：002实际成功的pregrasp Z=1.03357000698 → 原full-window Gate → +10mm到height recipe pregrasp Z=1.04357000698 → 原full-window Gate → 原grasp → Gate → close0.50/hold250 → 原25mm lift/native escape/postlift Gate。`route_pregrasp` 以pregrasp结尾，因此原online_window分类仍为pregrasp，不会误放宽为grasp。任何规划/window失败立即停止，不能闭爪或继续下段。

`route_spec.json`绑定002成功plan/window及height recipe ID。主调度应将route spec文件hash与所有runtime源纳入manifest；不得在运行时改route。保留postlift_roll revision=2；这是pregrasp_route revision=1，不重置物理失败计数。

`route_geometry_audit.json`：新增10mm段11个固定线性样本，实际native开手掌/双指相对table/pad/bottle无相交，原Robot入口roundtrip通过。仅末端手几何采样，不是完整手臂IK或CuRobo实际路径证明；真实每段仍由审计world规划与full-window约束。

CPU：原run生命周期4tests和实际execute()回调替换测试4tests全部通过。后4tests覆盖成功恰4query、三处规划最早失败、三处window最早失败及lift失败不出第五次query。都是fake scene/CPU，不初始化CUDA或新Scene。普通异常/trace保存/cleanup仍沿原v2行为。

预算上界：1 fresh scene、1 action scene、4 single-query、0 collection。尚无manifest/实际GPU执行。首段即使复用了002的成功目标，也仍是新场景真实重新规划，不复制旧控制或宣称保证成功。

Prefix扩展设计暂停处理，但精确计数已确认：旧调用链micro3 +补足15mm/40mm两次 + clearance_raise/center_high两次 +共享V七点=14single；若接此V3新route micro则需15single。不能继续引用14作为V3整条上界。
