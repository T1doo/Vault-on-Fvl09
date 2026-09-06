# F3 唯一 COM-station 修订：CPU 必要条件通过

`recipe.json` 冻结 `f3-r3063-com-station-plus13p1mm-v1`，保留旧 top-down proposal ID/文件哈希、旧 r3063 几何父链。原数据和旧 recipe 不改。

唯一改变是抓取站点沿初始瓶体 local+y 的桌面投影平移13.1mm；使用此次真实 scene_binding 中的初始瓶子朝向。完整三维方向及高度保持后的向量都在 recipe 里：原始轴带微小竖直分量，明确投影到XY并归一化以严格保持抓取高度，不悄悄改变深度。grasp/pregrasp 同移，12cm间距、朝向、close0.50、hold250、lift25、速度、质量、摩擦和判据全部不变。

`closure.py`/`inner.py` 是旧必要条件程序的隔离参数化副本，删除固定 proposal 输入/输出路径，未改几何判据。五个闭合比例的 native mesh 支撑/掌部检查、双指可达同一原生瓶体片、双内表面同截面条件全部通过；原 Robot.left_plan_path AST 提取入口的 actual→reported→solver 往返通过。`cpu_audit.json` 汇总且绑定 recipe/详细结果哈希。

这些是离散必要几何条件，不是连续碰撞、全臂 IK、抗转矩或物理成功证明。当前新 scene/IK/physical 均0；下一物理结果仍须原20mm/5mm/0.05rad/50帧 Gate。

实际 COM 读取 helper：`live_mass_properties.capture_mass_properties(scene.bottle)`，仅在主调度已创建的 fresh scene 中调用，不自行创建场景。依据锁定 SAPIEN physx.pyi `PhysxRigidBodyComponent.get_mass/get_inertia/get_cmass_local_pose`（825–835附近）；输出实际质量、惯性、局部COM pose与世界COM、actor/component身份。缺失/多重刚体或无效值立即报错，不用代理回填。三个无GPU fake-actor测试覆盖wrapper、多个组件拒绝、坏质量拒绝；真实API在fresh scene尚未调用。

一次 CPU freeze 在两份几何结果已成功写出后遇到 numpy.bool_ 的 JSON 序列化错误；recipe和详细结果保留。修复为显式bool，随后只调用 finalize 发布摘要，没有重跑几何、更没有GPU。
