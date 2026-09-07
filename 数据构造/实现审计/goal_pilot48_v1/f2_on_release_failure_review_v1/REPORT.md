# F2 on release：已保存状态的独立 CPU 根因审查

2026-09-07。仅读取已消费的 `p48_f2_on_beside_qualification_001/on`；没有创建Scene、调用IK/MotionGen或GPU，没有重试、改源、改账或接受raw。

## 结论

当前直接证据是**精确release目标与原attached-can安全外扩模型有冲突**，不是已证明的数学不可达，也不是已发现的抓持/frame/锁关节接错。
第二个高层MotionGen问题返回IK_FAIL，valid_query=true，内部attempts=10；未保存任何候选IK解或position/rotation error，因此不能断言所有解不存在，也不能排除其它机器人姿态限制。
第一段preplace已实际成功；第二段未执行，未打开夹爪。首失败停止，beside完全未尝试。

## 实测与离线重建证据

- `model_014_on_full.json`中full single/batch start均valid；真实两个锁关节为0.026446541771292686、0.024166883900761604，全部rollout锁值与config及末帧实际qpos相同，query start也逐值等于末帧38关节。
- 50个world shape反推出相同实际solver base；URDF末帧flange对真实trace矩阵最大误差2.984e-7。原reported-goal工具/基座变换由冻结Robot/planner函数CPU提取，不把该经验变换用于物理world几何。
- `release_goal × prefix_actual_T_eef_can == nominal_target_actor`最大矩阵误差2.22e-16；预放执行后实际grasp微变若重新算goal，仅平移约0.170mm。按实际solver FK/grasp投影到原release目标，can位置与名义target约差0.165mm，不是厘米级错frame。
- 原189个attached-can球及原4mm collision_sphere_buffer在目标处有4个负pair，**全部是attached_can/scale__0**：最差−3.42134mm，另外−0.29978、−3.37908、−2.57139mm。没有其它world负pair。
- 同一球组仅去掉buffer的只读诊断为0负pair。这不是建议删除buffer，也不是GPU模型重新验证。
- 名义target及实际grasp/solver隐含target的native can均无world材料相交。scale__0最高Z=0.780326747m；隐含target的native最低Z≈0.781837673m，仍高约1.511mm。功能点Z=0.781787832m本来就比native秤面高约1.461mm，故不能把该放开前目标称作已真实物理支撑。

附加边界：这只是目标处的attached-can模型必要检查，不含未知目标IK姿态对应的全机器人碰撞，不证明路径、连续sweep、物理稳定或最终on成功。目标附近的位置/姿态容差可能容纳偏移解，所以即使精确目标有负pair，IK_FAIL仍不是数学无解证明。

## 唯一建议：一个由原4mm buffer直接导出的release waypoint微调

只建议新版本将**on放开前release waypoint沿world+Z抬4mm**，不搜索候选、不改preplace/retreat/rest，不改名义metadata支撑目标与原on footprint/高度/支撑/排他/速度/rest验收，也不改100settle+75rest。
4mm直接取本次原配置的collision_sphere_buffer；保留全部189球及4mm buffer、全部50world shape、机器人碰撞与原数值阈值，**不新增scale例外、不关整个scale、不改模型或资产**。
`SINGLE_REVISION_PROPOSAL_001.json`对这一唯一位移离线重算：目标attached-world负pair=0，native目标无材料相交；放开前native最低点距秤面约5.511mm。
这意味着on原本约1.511mm的放开后下落增加4mm，必须如实记录为新release recipe、重新真实验证100帧settle及最终关系，不能称完全相同的物理动作。原inside的受控支撑/禁止主要重力drop规则不能反向套用或偷偷修改on；这里也不借inside窄接触许可。
此为提案，未做新IK或物理；如果目标机器人姿态/路径仍失败，应保留证据并停止该修订，不自动加scale例外或继续抬高。

## beside与下一有界入口

beside没执行，不能算失败，更不能从旧清单拿剩余额度直接续跑。可以独立新job/output/有限reservation，1fresh scene真实canonical replay、原current/anchor/prefix门、4个suffix问题、1action、0collection、10高层状态检查；不重复clearance资格、不恢复旧held-state。
on修订若采用同样必须新namespace、独立源锁和完整Guard；整个F2三关系root仍未完成，本审查不改变任何成功分母。

产物：`ANALYSIS_001.json`绑定原trace/model/goal/URDF源，`SINGLE_REVISION_PROPOSAL_001.json`绑定原审查及唯一样本，`analyze.py`/`propose.py`为可重算CPU实现。原运行文件保持不变。
