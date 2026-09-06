# 定向修复：已夹持、仍受支撑的瓶子不能被当作非法起点

## 实际证据

本次r3063替换真实完成pregrasp/grasp，并通过两段原full-window Gate；实际close0.50、hold250完成。最后25mm lift未执行，因为MotionGen报`INVALID_START_STATE_WORLD_COLLISION`。

`F3_POSTCLOSE_SUPPORT_MODEL_CPU_AUDIT_V1_20260906.json`复核真实1404行trace和完整postclose配置：

- 最后250帧均有双侧真实夹指接触、均有瓶子—pad支撑接触；原物理classifier下禁止碰撞0、信号完整。
- 相对EEF的瓶体漂移最大0.00006772m / 0.00032076rad；这只支持“受支撑的保持阶段稳定”，不证明承重抓取或离台成功。
- 字面模型球与实际mesh的负间隙全部为`attached_bottle ↔ pad__0`，7对；没有其他机器人/世界负间隙。
- 最深模型球负间隙约4.858mm，其中原配置buffer为4mm；即使只去掉buffer，仍有2个半径1mm的采样球穿过pad平面，因此简单调小buffer不是完整解决方案。
- native瓶体最低点相对pad top约-0.05265mm，真实末帧支撑接触由原classifier确认；不能把支撑接触或接触求解的微小几何误差直接当作非法任务状态。

CPU字面配置审计不冒充一次新的真实CuRobo查询；它结合已保存的求解器错误、实际状态/FK和原始model sphere参数定位模型问题。

## 修复实现及边界

`support_pair_collision_v1/policy.py`实现两个世界检查视图的按sphere-link合并：

1. 所有机器人球仍使用完整世界，table与pad都不关闭。
2. 只有`attached_bottle`的球使用缺少`pad__0`的视图；table、对臂及其他障碍保留。
3. 仅接受已验证250帧稳定、双指接触、支撑接触、无禁止碰撞的postclose证据；其他world对象丢失、球索引变化、全局关闭obstacle、单边world更新全部拒绝。
4. 覆盖unswept/swept × distance/collision四个入口，保留机器人梯度；distance使用库规定的`return_loss=True`，避免对mask后梯度作错误假设。
5. 必须在MotionGen/IKSolver构造**之前**传入。锁定版PrimitiveCollisionCost会缓存`coll_check_fn/sweep_check_fn`，事后只替换world对象方法不保证生效。

`factory.py`提供实际MotionGen接入接口，并设计了两视图真实Warp缓存、实际sphere-link索引、所有rollout已缓存callback的核验。它当前**仅完成代码接线，尚未在GPU执行**。

放宽的只是为规划该接触脱离动作而选择性处理已确认的瓶子—pad支撑关系，不允许任意穿入支撑面：返回规划控制后，必须由`audit_lift_escape`检查250Hz native瓶体几何下包络不向支撑面深入、最终离开支撑、计划actor上升至少原20mm。它是离散规划筛查，不冒充连续碰撞证明。原实际tracking、接触、禁止碰撞、20mm/50帧/5mm/.05rad物理Gate全部不变。

8项CPU回归已通过：四入口只改附着球、distance梯度路由、禁止全局关障碍、拒绝未同步world、拒绝丢其他障碍、拒绝非法支撑证据、拒绝下沉/无抬升计划、拒绝sphere分区变化。GPU核、真实规划曲线和物理抬升仍未验证，不能宣布F3修复成功。

## 下一项最小验证提案（未授权执行）

优先用已保存postclose状态做零新scene、零physical、零raw的单次模型核一致性验证：完整世界应重现原起点拒绝；pair-aware视图只解除瓶子—pad的该项冲突；robot-pad与bottle-其他障碍检查仍必须保留。合并的小范围提案限定4次高层起点检查，通过后最多一次lift规划并校验所有插值点native几何，不执行控制，timeout1800s。详见`F3_POSTCLOSE_MODEL_SINGLE_PLAN_PROPOSAL_V1_20260906.json`，当前未授权。

原替换范围已消费：累计4scene/6IK/4trajectory/2attempt slots。新验证不得伪装成原替换的剩余额度，不自动重跑物理micro。

此设计目前仅审查F3具体`attached_bottle/pad__0`，不自动推广为F2的can-table释放规则。F2还需要“到位支撑→对象留在目标→开爪回撤”的完整模型状态接线与独立审查。
