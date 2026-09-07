# 统一 readiness：Pilot 输入24/48，科学 Stage 1 未完成

日期：2026-09-07。本文是已核验状态快照，不是新执行授权；后续增量以`goal_pilot48_v1/STATE.json`、`pilot_cells.json`及正式日志为准。

## 当前已接受的输入

| 家族 | Pilot A | Pilot B | 已验收/目标 |
| --- | --- | --- | --- |
| F1 物体选择 | 3 r_pc＋3 r_inv_path | 3 r_pc＋3 r_inv_motion | 12/12 |
| F2 目标—关系组合 | 未形成完整组 | 未形成完整组 | 0/12 |
| F3 低层事件顺序 | 未形成完整组 | 未形成完整组 | 0/12 |
| F4 高层子任务顺序 | 3 r_pc＋3 r_inv_path | 3 r_pc＋3 r_inv_motion | 12/12 |
| 合计 | | | **24/48** |

这24条是当前用户Goal下已验收的pilot输入，不是360正式轨迹的一部分。F1/F4各A/B的六格完整；不能把它们当成正式R=3的九轨迹root，也不代表整个科学Stage 1或temporal identifiability Gate完成。

F4-B最终六格独立审计：`goal_pilot48_v1/f4_b_pilot_acceptance_v2/FINAL_AUDIT_001.json`，receipt `0b44d845f9472514c665e09f502fc58b182da251e57d2eee202a2069df43a487`。主线程登记：`pilot_registration_v1/F4_B_ADOPTION_001.json`，receipt `5ed6e10281a97a86234b6baf0019855bf1ea5e02519c64923819fe26d1aac1a8`。原18格原内容保持，旧表精确UTF-8备份已保存；重复登记检查通过。

F4-B原Guard因其他用户占GPU7未在初始冷却窗观察到idle，仍保留false。后续真实严格idle、原PID/PGID退出及原文件不变证明以独立late-release receipt追加，不把旧失败改写为成功。该资源问题已经结账解决，不应再次重采六条数据。

## F2/F3剩余问题与权限边界

- F2：`p48_f2_prefix_clearance_001`真实抓取、12cm抬升、原prefix物理门及fullworld恢复通过，Goal receipt `0e859a2b2f96501ec9fa156d7c0afe84c5faffde80d2479cdb636328d4987337`。这不是具体放置或三关系root成功。
- F2 inside：用户已批准native包络与真实箱底几何边界修订；尚未批准改变旧held-transport中禁止can/box接触的规则。仅最后下降、精确box__9接触的窄例外另待决定，当前原全窗口门保持，公开inside issuer拒绝签发。不得通过漏行、切窗、扩大box碰撞白名单绕过。
- F2 on/beside：四段、实际释放后模型、原100步settle/75步rest及原关系门已有CPU实现。双fresh-scene资格外壳仍在最终准备，未运行新放置验证；该范围不依赖inside接触例外，但两分支通过不能代替三关系root。
- F3：横放抓持第三版在真实提起后仍持续滚转，5mm/0.05rad门失败，旧三次稳定修订上限已用完。竖直同资产侧夹的新设计及最多23solver/2scene资格轮次仅为待批准提案；不得把自动Goal续跑当新批准或改名重置预算。

## Goal尚未完成的必需项

1. F2、F3各A/B共24条输入及完整三候选组验收。
2. 预先冻结同一版本集合、跨至少两家族的连续至少六条真实采集；尚未通过，不能事后把零散作业拼成连续段。
3. 全数据的无训练结构、负例、时间对齐和模型可见字段/泄漏检查。现有登记一致性测试不替代这些检查。
4. 正式40 primary＋16 ordered reserve的完整生产草案及剩余生成器/预算等待冻结项。当前草稿不是执行许可。
5. 最终报告逐项对照整个Goal证据。

Stage 0仍封存。正式360执行、训练、H-reveal、compression和π0.5未授权；科学Stage 1完成未被证明。当前无新GPU作业或活跃预留。

当前Goal已结账资源为2283 solver、39 fresh scenes、27 action scenes、6 collection attempts、7200 GPU lease秒；这是当前Goal累计消耗，不是成功轨迹计数，不包含所有历史试验。完整失败与恢复链见正式日志§533–568及各后续条目。
