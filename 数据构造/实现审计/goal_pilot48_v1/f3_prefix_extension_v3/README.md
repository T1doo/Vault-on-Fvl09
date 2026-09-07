# F3 第二fresh微门 + 原shared V：独立CPU扩展V3

仅CPU接线，旧prefix_extension_v1/v2暂停历史、冻结v5/tangent均不改。入口 `controller.run(manifest)`，测试入口 `test_all`。没有manifest/budget/GPU执行。

## 必要前置与范围

必须已有同一recipe3/route2的**第一次fresh v5微门成功**、完整world恢复两路valid、Guard清理通过。manifest需额外绑定 `prior_micro_terminal_path`、`prior_micro_guard_path`、`prior_micro_manifest_path` 于input_files，并提供expected_recipe_id。三份旧文件重核self-hash、parent manifest/recipe/route/独立job身份；缺失或失败不得创建新场景。它们不能是006失败，也不能把本次job自己当第一确认。

第二场新scene先执行原v5微门（3single），包含原supported/tangent选择、actual native escape/fl3-fl5、原postlift Gate和完整world恢复。微门pass不足：恢复记录必须恰single/batch两键且严格valid=True；证书过期、实际checker不能仍带pair例外。全部通过才先写 `second_fresh_micro_pass_before_continuation.json`，再执行extension。该文件是第二微门的独立事实；后续prefix失败时不得把它改写成微门失败，也不得把它升级为prefix成功。外层沿旧run生命周期，仍以最终prefix结果判断整体micro_pass字段；调度者应同时读取该独立文件和prefix_result，不能只读一个旧顶层布尔值。

## 精确调用链与预算

原v5三次 → 从实际EEF向上15mm补原4cm段 → 从实际EEF向上40mm补原8cm段 → 原clearance高度审计和clearance_raise/center_high两目标 → 原中心hold/preV Gate → 原七点V每点hold50 → 原event metrics、接触、边界相对变换/静止验收。

总3+2+2+7=14 single，1scene/1action/0collection；原v5高层model checks正常6次，扩展复用已恢复模型不额外构造或放宽世界。原V=.055m、table Z、七点 `[+.5,+1,0,-.5,-1,-.5,0]×.055`、250Hz、50帧保持、center原2x time dilation均不改。

`locked_tail.py`从实际family_runners_v3_3 post8cm至prefix返回完整复制，AST重核与原段相同。只以私有globals替换actual→reported规划入口及执行前nativefl3/fl5；原preV/event/postV/relative验收函数未改，不调用旧grasp chooser。每段carry在原time-dilate后再检查实际要执行的controls，任何native失败不执行。完整attached世界始终保留pad对瓶约束；本扩展不使用support例外。

## Trace/marker完整性

私有克隆v5 execute/inner，在真正postclose attach调用时记录当前trace行；postlift原审查hook只从该次实际lift receipt的end_trace_row读取早期pose，而不是拿确认窗最后pose冒充lift结束。trace index、step、timestamp、actual EEF/actor/relative pose一起绑定，重复相同marker不同位置会报错。

原tail另外以AST插入6个记录hook：8cm lift后、clearance后、center后、preV、postV、acceptance_end；旧event_0_V_start/end保留。每段实际执行前后也记录marker。postclose hook行必须与原postlift baseline相同，禁止移基准。中途失败时finally保存已观测boundary records，原run继续保存trace并清理Scene。

实际prefix数组保存为diagnostic `shared_v_extension/prefix_arrays.npz`，摘要与哈希在prefix_result，不产生训练raw/root。generic dispatcher若以后接入，kind保持F3_MICRO才能继续对账局部trajectory_queries与总meter；局部run计数通过只在私有AST把3上界改14，原v5源和微门内部3次限制不改。

## CPU核验

14tests通过：最早错误/微门失败/空恢复禁止后续、目标派生、14预算、七点table-Z、早期pose不被末帧替代、原tail六hook结构、第一确认条件、私有14-query run生命周期和主/次保存错误。原tail AST逐节点等价验证，CPU_AUDIT绑定全部源。

测试第一次用unittest assertEqual比较numpy数组导致测试自身歧义错误，改为np.array_equal后全过，没有修改算法/Gate。尚未GPU或真实prefix运行；此CPU覆盖不能证明实际规划、持物稳定或全臂连续碰撞自由，仍必须实际执行后由原Gate验收。
