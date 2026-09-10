# F1完整生产计划

目标：10个有效root×9格=90条；四个按rank激活的reserve替换失败主槽。旧pilot不计入90。所有当前执行授权false。

| root | split | 难度 | 左→右对象 | 红/绿/蓝X（m） | 公共盒XY（m） | 目标cell |
|---|---|---|---|---|---|---|
| F1_000001 | train | clear | red/green/blue | -0.23000/-0.09754/0.00927 | -0.0800, -0.1600 | 3×3 |
| F1_000002 | train | medium | blue/red/green | -0.12292/-0.03372/-0.22800 | -0.0780, -0.1600 | 3×3 |
| F1_000003 | train | medium | green/blue/red | -0.03231/-0.22600/-0.12120 | -0.0760, -0.1600 | 3×3 |
| F1_000004 | train | medium | red/green/blue | -0.22400/-0.11949/-0.03090 | -0.0740, -0.1600 | 3×3 |
| F1_000005 | train | crowded | blue/red/green | -0.14160/-0.07009/-0.22200 | -0.0720, -0.1600 | 3×3 |
| F1_000006 | validation | medium | green/blue/red | -0.06834/-0.27500/-0.16386 | -0.1250, -0.1350 | 3×3 |
| F1_000007 | validation | medium | red/green/blue | -0.27300/-0.16215/-0.06686 | -0.1230, -0.1350 | 3×3 |
| F1_000008 | test | clear | blue/red/green | -0.06008/0.04994/-0.18500 | -0.0350, -0.1850 | 3×3 |
| F1_000009 | test | medium | green/blue/red | -0.00190/-0.18400/-0.08478 | -0.0340, -0.1850 | 3×3 |
| F1_000010 | test | crowded | red/green/blue | -0.18300/-0.10657/-0.03937 | -0.0330, -0.1850 | 3×3 |

每份spec完整绑定三44mm方块（颜色identity）、共同塑料盒、两个相似干扰物及背景物的位姿、尺寸、材质和资产文件hash；它们是继承成熟F1 primitive的实际对象，不把方块改称罐子。模型候选表达拾取具体颜色对象并放入同一公共盒，内部ID仅供audit。

四路模型相机front/head/left/right，320×240；原生捕获必须同t0保存RGB、state和完整相关anchor并读回，再开始动作。CPU投影只用于冻结规划难度，实际可见性/遮挡/抓取净空仍是首批和逐root真实资格项。

同root的r_pc三条共享真实canonical动作前缀；r_inv_path固定臂、同对象/程序，在safe_horizontal运输段偏移Y=15mm；r_inv_motion在注册post-prefix位置额外hold35帧。250Hz不变，阶段和实际effective控制独立重算，不能凭总长度或整体路径差异通过。

正式non-task位置阈值3mm应用于从t0起所有已记录状态；历史provisional10mm不再隐式进入本版验收。具体信号/单位/阶段以spec.f1_verifier_contract为准，目标释放与支撑依据真实状态及物理接触证据。

同一全族manifest和ledger覆盖所有wave。首批为F1_000001、F1_000002两个train root；完整18条与副本/资源检查通过后自动继续000003—000010。正常失败有界恢复，次数耗尽按完整terminal barrier及原主rank分配备用；共享代码或观测问题阻止放量。

备用000011—000014尚无观测/anchor/prefixhash；激活时使用已冻结generator、seed和继承split/difficulty形成实际spec，原planned slot不改。替换再次失败仍追溯同一原主槽，不因完成顺序抢备用。四备耗尽则family incomplete，不能加root或降低R。

split固定5 train/2 validation/3 test；难度总配额2 clear/6 medium/2 crowded。root及所有分支、realization、派生view保持同split。未通过root仍保留失败分母。validation/test不得用于调参后再叫untouched；相关修复影响集中登记。

尚待原生确认：当前安装版本相机同步/renderer UUID、实际初始观测相等、所有新布局可达与三对象可抓、接触支撑和释放、真实阶段记录，以及CPU/GPU时间、RSS、磁盘增长。CPU fixture不证明上述物理事实。

机器入口：manifest.json、specs/*.spec.json、NINETY_CELL_PLAN.json、PLANNED_SLOTS.json、RESERVE_RULES.json、F1_BUDGET_REQUEST.json。唯一执行交接见LUNA_F1_FULL_PRODUCTION_HANDOFF.md。
