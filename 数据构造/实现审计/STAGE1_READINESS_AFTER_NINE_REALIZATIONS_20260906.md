# 统一 Stage1 readiness：9条变体已验证

状态：`NOT_READY_F1_F4_VARIANTS_VERIFIED_F2_F3_MODEL_GATES_PENDING`。

| Family | 已验收开发根 | r_pc | 新路径变体 | 新速度变体 | 开发原始轨迹合计 |
|---|---:|---:|---:|---:|---:|
| F1 | 5 | 15 | 3 | 3 | 21 |
| F4 | 1 | 3 | 3 | 0 | 6 |
| 合计 | 6 | 18 | 6 | 3 | 27 |

F2/F3尚无完整验收开发根；其局部成功和失败诊断保留，但不并入上表完整根分母。

本次新增9个真实rollout已验证，补充的是3个既有root，不是新增3个独立root。F1-A三path、F1-B三motion、F4-A三path均整组通过；F4原三r_pc+新三path合计6条的最终状态等价也通过。raw/video/root/index以及18格旧新配对证据已独立复核。

首条曾因UTF-8回执写入失败，通过原trace和原predicate的CPU重建另存派生receipt；没有再执行该轨迹。原source mismatch和UTF-8失败终端均保留。累计10scene/123queries，未超用户批准预算。最后GPU3已恢复15MiB/0%/P8且无本任务进程。

三个6-cell pilot证据矩阵完整，共18个候选复用格，但无阶段授权：**Stage1仍0/48、formal仍0/360**。不自动promotion，不开展训练、H-reveal、compression或π0.5。

下一步是F2固定终点约束分解与F3实际gripper/world模型修复，按此前条件许可先完成CPU绑定和前置检查；不重发已消费的旧transit/micro job。

交接：`GPT_HANDOFF_NINE_REALIZATIONS_VERIFIED_20260906.md`。机器状态见同名JSON和`REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json`。
