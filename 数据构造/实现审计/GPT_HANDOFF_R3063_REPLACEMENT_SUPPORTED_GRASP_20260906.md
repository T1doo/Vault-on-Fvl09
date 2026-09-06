# r3063替换结果：真实接近/抓取/闭爪通过，lift停在支持接触建模

用户明确批准了原bootstrap失败后的一次替换。本次已执行，原失败及全部计数保留；不是另起无限重试。

## 真实结果

- trace初始化遗漏已修复，current/anchor与1404行真实诊断trace完整保存。
- pregrasp、grasp两段实际执行，均通过原full-window Gate。
- close0.50及hold250真实完成。最后250帧双指物理接触250/250、瓶子-pad支撑接触250/250、原classifier禁止碰撞0、信号完整；相对EEF漂移max **0.06772mm / 0.00032076rad**。
- 这说明新top-down方案能进入接触并在受支撑状态保持，**不证明承重抓稳或离台抬升**。实际指关节0.03157/0.03096m，命令drive target0.0175m，未把command当作realized qpos。
- 第三次规划已从实际postclose状态发起，目标是actual EEF向上25mm；MotionGen立即报`INVALID_START_STATE_WORLD_COLLISION`，没有执行lift，原postlift Gate尚未通过。

本次基础设施终端`pass=true/error=null/trace_save_error=null`；科学micro仍`micro_pass=false`，两者不能混写。

## 根因证据比“又没抓稳”更具体

`F3_POSTCLOSE_SUPPORT_MODEL_CPU_AUDIT_V1_20260906.json`用原始postclose配置、实际qpos、经trace校验的URDF FK和native世界mesh重算：

- 全部7个模型world负间隙都在 **attached_bottle ↔ pad__0**，最深约4.858mm。
- 机器人自身各球对该world没有负间隙；实际保持期原物理规则也未发现禁止碰撞。
- 模型原buffer为4mm，但只减buffer仍有两个半径1mm的采样球穿入pad平面，所以不能简单改buffer了事。
- native瓶体最低点相对pad顶面约-0.05265mm，实际支持接触由原物理classifier确认。瓶子本来就应在抬升起点接触支撑面；将其无差别当成碰撞禁区，会让支持→离开动作无法开始。

这里的球几何重算是CPU审计，不冒充新的真实CuRobo kernel检查。

## 已实现的定向修复，尚未GPU验证

`support_pair_collision_v1/policy.py`、`factory.py`与`test_policy.py`：

- 所有机器人球继续使用完整world，table/pad不关闭。
- 仅附着瓶子的球使用排除已确认pad__0支撑面的检查视图；table、对臂、其他障碍仍保留。
- 覆盖静态/扫掠×距离/碰撞四入口，并保持距离梯度。
- 构造MotionGen之前传入，核验真实缓存与全部rollout已缓存callback；避免“改了world方法但实际优化器仍调用旧函数”。
- 必须用完整250Hz计划native几何检查不进一步进入pad、最终离开支撑和原20mm计划升高，再保留原实际postlift/tracking/contact Gate。离散筛查不冒充连续碰撞或物理成功。
- 8项CPU测试通过，包括保留robot-pad检查、其他障碍不能被删、梯度路由、四入口、非法支撑证据和下沉计划拒绝。

**GPU factory、实际kernel、计划曲线和真实抬升尚未验证。**没有新GPU执行manifest，没有暗中追加物理尝试。详细影响审查见`SUPPORT_PAIR_MODEL_REPAIR_IMPACT_REVIEW_V1_20260906.md`；此实现目前只针对F3的瓶子-pad，不直接替代F2 can-table释放模型。

## 资源与预算

本次：GPU7，UUID `GPU-4c836e67-fb8e-a993-002c-cb83b10a6ead`，Guard2698362/child2698383，109.74s。scene/Guard cleanup和baseline通过，独立host确认GPU7=14MiB/0%/P8/no compute、两PID退出。

本次消费1scene/3trajectory/1attempt；加此前StageA和原bootstrap失败，累计 **4scene / 6IK / 4trajectory / 2physical-attempt slots**。其中只有此次替换实际执行arm controls。原批准的替换总预算已用完。

F1/F4仍6开发root/27raw，pilot候选18格；Stage1=0/48、formal=0/360，均未扩授权。F2模型接线和F4-B预算差额仍在原交接中，不能误报本轮已经解决。

## 建议下一步：先验证保存状态中的模型，不再直接重复整个物理尝试

建议另行批准一个最小的**零新scene、零physical、零IK、最多一次条件lift规划**模型核验证作业，使用此次保存的真实postclose状态与native几何：

1. 完整world在single/batch模型上重现起点拒绝。
2. pair-aware模型在同样single/batch配置上检查该支持起点。
3. 实际Warp cache、sphere/link partition及所有rollout callback必须一致；机器人-pad与瓶子-其他障碍检查不能丢失。

上限为4次高层起点constraint检查，以及全部检查通过后最多1次lift规划；底层实际kernel调用另记，timeout1800s。规划后只做dense-native几何审查，不执行控制。完整小范围提案见`F3_POSTCLOSE_MODEL_SINGLE_PLAN_PROPOSAL_V1_20260906.json`，当前approved=false；不自动重跑物理micro、不下调“两候选确认”规则、不进入sharedV或full root。

输出目录：`/nfs_share/lijunhui/Robotwin2/datasets/f3_r3063_bootstrap_replacement_v1`。

当前机器状态：`STAGE1_READINESS_R3063_SUPPORTED_GRASP_LIFT_MODEL_BLOCKED_20260906.json`。所有旧状态文件保留为历史快照。
