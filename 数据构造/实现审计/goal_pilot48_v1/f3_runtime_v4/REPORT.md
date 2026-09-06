# 路径修订2 + native fl_link3/fl_link5 执行前检查

第三稳定recipe和+12mm grasp不变，不是第四稳定配方。新路径只保留005已通过原full-window的低pregrasp Z=1.03357000698作为最终pregrasp，直接到冻结grasp，approach108mm；不再执行1.04557高pregrasp。不变close0.50、hold250、lift25及所有物理参数/Gates。

`route_spec.json`绑定005低pregrasp真实plan/window、第三recipe、URDF及实际native形状capture。`micro.py`读取manifest recipe/route路径，Scene创建前核对这些源哈希；独立新命名空间，旧v3及所有失败不改。

新增每段生成真实GPU controls后、任何控制执行前的native pair gate：读取实际完整命名qpos、把六个锁定左臂solver joint controls按名替换，用原URDF FK和实际SAPIEN collision mesh逐点检查 **fl_link3↔fl_link5**。actual right link3/5 capture与left URDF collision逐项相同验证后才复用native顶点/三角片/localpose，不用CuRobo近似球。检查结果单独落盘；任何相交立即停止，未执行的计划保留。

独立保存轨迹回归已证明：004同段planned controls和真实trace均0相交；005高pregrasp planned controls有57个离散相交样本，真实trace尾55帧相交。故这项检查可以在005那次已保存计划执行前拒绝，而非只事后解释。详见 `../f3_native_self_pair_v1/regression.json`。

范围必须如实限定：当前是已观测一对link的离散native检查，不是全臂所有自碰对、更不是连续时间碰撞证明；原full-window中所有碰撞/跟踪门保留。新增108mm grasp路径尚无实际控制，因此不能预先宣称安全；必须GPU生成后过本gate及原world planner，再真实执行并过原window。不能把旧004高段通过当成新路径已通过。

CPU共9tests通过：四个run生命周期、两处preclose plan/window最早失败、lift失败不出第四query、成功恰三query、native拒绝发生在首个_execute前。主调度签发时最多3single/1fresh/1action/0collection，并将checker源加入绑定。无GPU/manifest签发。

prefix_extension先前15query版本仅暂停草案，尚不可执行。若以后以此3query micro接同链，计数需重新审计，不能引用暂停代码的硬断言4/15。

签发前主线程复核要求的收尾：native geometry读取已显式UTF-8；空controls、错误维度在加载原生几何之前立即拒绝，不允许all(empty)误过。新增2项负例后合计11tests全过。`../f3_native_self_pair_v1/contract_hardening_recheck.json`绑定最终checker/test哈希，重新实际计算004/005原生回归并逐字典比对原regression一致，原报告不覆盖。此收尾未改v3或任何已执行源，未运行GPU。
