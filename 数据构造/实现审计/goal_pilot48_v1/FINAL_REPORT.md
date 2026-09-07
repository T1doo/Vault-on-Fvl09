# Pilot48 Goal 交付报告（进行中草稿）

本文件不是完成声明。实时状态以 `STATE.json`、逐任务不可变终端及正式日志后续记录为准；不得把下表的开发检查通过当作完整数据或科学Gate通过。

出版阻塞已由用户当前明确授权解除，45d7ff4推送成功。F2-U已实际通过全部3IK和4段carry/release规划，物理三关系root仍待执行。F3 V5已通过36项CPU测试，尚未GPU验证。

## 完成条件

| 条件 | 当前结论 |
| --- | --- |
| 四族完整三分支采集 | 未完成：F2/F3仍缺完整合格根，F4-B验证中 |
| 八个pilot根、48条输入 | 18/48已显式复用验收；本Goal尚无新合格完整轨迹 |
| 六条跨至少两族冻结版本连续采集 | 未开始；须从尚未采集格子预注册，不重采已成功数据凑数 |
| 独立raw/trace/video/current/anchor/实现变化验收 | 已有18格完成，新30格待实际生成后逐格验收 |
| 正式360生产草案 | 尚待完整采集入口验证后定稿，不代表执行授权 |

## Pilot矩阵

| 族/根 | 需要的真实实现 | 已验收输入 |
| --- | --- | --- |
| F1-A | 3 r_pc + 3 r_inv_path | 6/6，复用 |
| F1-B | 3 r_pc + 3 r_inv_motion | 6/6，复用 |
| F2-A | 3 r_pc + 3 r_inv_path | 0/6 |
| F2-B | 3 r_pc + 3 r_inv_motion | 0/6 |
| F3-A | 3 r_pc + 3 r_inv_path | 0/6 |
| F3-B | 3 r_pc + 3 r_inv_motion | 0/6 |
| F4-A | 3 r_pc + 3 r_inv_path | 6/6，复用 |
| F4-B | 3 r_pc + 3 r_inv_motion | 0/6 |

已有18格证据与不可变来源在 `pilot_cells.json`；全部历史开发raw数量与选定pilot矩阵是不同分母。

## 已排除的错误方向与剩余问题

- F2：固定布局下U高度修订已实际通过C8/U8/D4完整合格解及四段持物/释放/空手返回规划，原生支撑和实际模型切换通过。新布局真实公共抓取及inside/on/beside物理root还需独立验证；旧suffix里的gravity-drop和80mm中转不能直接复用冒称新受控放置。
- F3：原抓法离垫后滚转；COM站点和抓取深度修订改善了漂移，但尚无完整合格微门。004原漂移门通过、实际升高19.911mm仍失败；不能四舍五入放行。005高接近段臂自碰已由保存controls的原生link3/link5检查重现。006低接近修复完成闭爪/稳定hold，但旧250帧pad支持certificate拒绝16/250的边界卸载状态，未lift。正在独立审查planner切触卸载模型证书，不改旧失败或原物理验收。
- F4-B：独立新布局source、三完整程序规划和五项物理isolation均实际通过，累计135+450+720目标问题。还需三template、root与motion，不提前算六条新输入。
- 公共入口：新 `runtime_v2` 在同一Goal账本下接入collection请求计数，CPU测试通过，尚待真正新collection验证；旧runtime没有collection hook，不能用于新完整采集后声称collection=0。新F1作业暂拒以防旧namespace动作漏计，已有F1输入无需重跑。

## 证据及复现入口

- 权限/研究边界：`USER_GOAL_SOURCE.md`、`GOAL.md`、`CONTRACT.json`。
- 精确运行：`jobs/*.json`绑定源、输入、预算和Guard；输出在工作区 `Robotwin2/datasets/<job_id>` 及相邻 `<job_id>_guard`、`<job_id>_meter`。
- 失败与资源：`attempts.jsonl`、哈希链 `budget_ledger.jsonl`，每个失败照计、旧作业不可重发；本报告不替代实时总账。
- 源配置：F1历史profile `9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72`；其他活跃profile `3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7`。官方tracked源不改。

## 始终未开放/未证明

Stage0仍封存。正式360执行、模型训练、H-reveal、compression和π0.5没有启动或授权；pilot输入齐备也不能自动认定整个Stage1科学Gate通过。所有CPU fixtures与诊断trace均不得充当成功raw或新增realization。
