# F2 on/beside接入新prefix后的执行影响审查

2026-09-07，主线程只读源码审查。本文不是GPU清单、成功回执或整root预算。

## 已证明与未证明

- `p48_f2_prefix_clearance_001`证明新固定场景的真实抓取/12cm抬升、原prefix物理Gate和fullworld恢复通过，提供真实current/anchor与可重放prefix。
- `p48_f2_u_route_001`证明其当次状态下beside C/U/D及四段carry/release规划通过，没有证明从本次新prefix实际末端开始的物理放置。
- 旧Stage0的on/beside成功保留，不自动继承为新布局整root资格。

## 旧采集入口仍需接线

| 分支 | 当前旧asset-bound采集入口 | 新实际执行应核对的接线 |
| --- | --- | --- |
| on | functional-point＋metadata几何推导目标，预放高10cm，4个target | 实际新T_eef_can；持物两段与真实释放后的空手两段分开建模/规划 |
| beside | 预放高8cm，加中间hub及返回hub，共6个target | 接入已审查的新U高度约47.9469mm与四段C→U→D→U→N路线；重新以实际prefix末端建模，不调用旧6段入口 |

源码依据：`controlled_multi_future/f2_asset_bound_runtime_v3.py:418`附近的`plan_suffix_from_actual_prefix_end_state`；on和beside均交给一次`_cache_suffix_controls`。该旧入口不是新F2 planner runtime V3的自动消费者。

新模型必须保持阶段区别：携带阶段从真实夹持状态拟合attached can；释放后从真实物体姿态和实际open joint状态重建static-can/fullworld，再计划退回。不能用预计D姿态替代实际释放姿态，也不能继续把物体挂在空手返回模型上。planner模型投影不允许改变模拟器物体状态或制造物理weld。

## 不把inside的门移植给on/beside

`family_runners_v3_3.py`的旧执行入口在持物阶段使用`audit_f2_held_transport_contacts`：on允许命名scale支撑，beside允许table支撑，支撑许可从release段开始；保留该接触身份/阶段语义。

旧on/beside为full-open后100步settle、退回/rest后75步观察；inside的250步settle、50步支撑及ReleaseSafetyV10属于inside专属要求。不得因共享新控制器而静默改变on/beside等待窗、成功阈值、支持对象或关系排他判据。on的metadata footprint/verifier并未随inside的native-floor批准一起改掉。

## 有限实现边界

每个on/beside suffix若维持两个持物目标、两个空手目标，理论下界各4个独立MotionGen问题，prefix使用已冻结控制时不新增solver，但新scene中的实际prefix replay必须计action scene。该数字不是完整root上限：仍须计入资格、实际建场、失败、task-feasibility、candidate冻结、strict replay、collection与变体，并由主线程在完整入口实现后冻结最坏预算。

GPU之前必须具备：

1. 新prefix/current/anchor及实际末端抓持变换绑定；不恢复旧held-state代替真实重放。
2. 路线与真实stage模型接线；碰撞例外只基于实际native/负pair证据，不能关闭整个table/scale或沿用inside box例外。
3. 原on/beside物理门、释放和final predicate明确调用；释放后的模型用实际观测而非预测姿态。
4. CPU失败传播/阶段次序/计数测试；随后独立fresh场景物理资格，不把旧规划通过说成新物理成功。
5. 三个关系完成同current/anchor、候选宇宙及原子root接受后，才登记F2 pilot数据。

当前只完成影响审查，尚未实现或执行上述on/beside新入口。正式360、训练、H-reveal、compression与π0.5不在范围内。
