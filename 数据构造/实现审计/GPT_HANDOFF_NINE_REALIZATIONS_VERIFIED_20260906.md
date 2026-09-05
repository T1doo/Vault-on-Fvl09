# 本轮交接：F1/F4九条真实变体已完成，下一步集中F2/F3

## 先说结果

最新外审指定的F1-A三条r_inv_path、F1-B三条r_inv_motion、F4-A三条r_inv_path，**9/9真实执行已验证，三个cohort均完整验收并发布**。不是CPU提案、不是旧轨迹加噪或重采样。

现有开发数据：6个独立root、27条raw（此前18+本次9）。其中F1五root/21条，F4一root/6条。F2/F3仍没有完整验收开发root。原F4采纳和全部Stage0封存不变。

F1-A、F1-B、F4-A各有6-cell pilot结构及物理证据完整的矩阵，共18个可复审格；**无Stage1授权，matrix accepted=false，Stage1=0/48、formal=0/360**。请不要把“证据齐”改写成“阶段已获批准”。

## 真实执行与验收

- F1-A：原第一accepted batch root，3 r_pc+3新path；仅冻结的非关键transport目标z+15mm，实际EEF差异超过原预声明阈值。三个分支、raw/video、current/anchor/prefix、root finalizer和publication index均通过。
- F1-B：原第二accepted batch root，3 r_pc+3新motion；实际新scene执行旧冻结控制的统一C1时间变换，保留边界位置/速度，记录实际ceil后的grid/执行时长。三分支均通过，0新solver query不是0物理执行。实际步数分别为green157→173/192→212/339→373，blue31→34/193→213/344→379，red203→224/178→196/324→357。
- F4-A：原已采纳root，ABC/ACB/BAC各新path；各30query，原family verifier及三分支最终世界状态等价通过。另将原三r_pc和新三path合并6条，用原0.03m/0.20rad comparator复核final-state equivalence，也通过；未放宽阈值。
- 最后cont8 job（只运行此前未尝试8格）pass=true，8新scene/112query/8新raw；加前面已完成首格，累计9真实新rollout/123query/10scene。10scene包含最早零动作source-mismatch场景。没有额外重试、没有首格第三次执行、没有新增独立root。
- GPU3 UUID `GPU-d5b84492-c467-0080-206f-2456cef0c338`；Guard1642824、child/PGID1643202，exit0、elapsed2801.37s，pre/launch/post/lease/cleanup齐全。独立host postcheck15MiB/0%/P8/no compute，两个任务PID均退出。

## 两个真实失败和修复，均完整保留

1. 首次V1在same-current入口失败。原F1 reference绑定9873bbe…，active/F4绑定3ec56ec…。已从Vault317387b恢复245-file精确旧F1源码到隔离worktree，namespaced adapter绑定原源、F4继续当前源，不回退active、不修改旧reference/hash。后续真实current/anchor通过。
2. 获用户明确replacement许可后，首条真实执行完成，但默认ASCII text writer遇中文source path导致回执截断。raw/manifest/sidecar/trace/MP4实际完整。原失败终端的unknown/0统计保留，CPU另行reconcile为11query/1raw。

首条使用原F1Controller verifier AST对保存trace重算9项predicate，通过；在6条既有F1轨迹上逐项回归一致，missing_support/outside_cavity反例均拒绝。11段实际effective position/velocity逐步匹配冻结控制，realized path variation也通过。派生receipt明确说明原ephemeral verifier丢失、替代验收为trace-derived，另存且hash绑定，绝不伪称找回原内存输出。原raw/video/失败文件都未改，首条未重跑。

后续IO改为显式UTF-8、exclusive atomic publication，reader显式UTF-8、Guard child UTF-8 mode。18项CPU测试及完整Guard入口通过后，只继续用户已允许但未尝试的8格；累计预算仍10scene/123query。所有新分支和最终发布实际成功。

一个额外CPU一致性问题也已明确记录：current storage拼接了共享Aloha articulation的left/right alias，存有两份相同38-DOF副本；原getter去重。提供无损解码和raw初始state0验证后，三个cohort的原机器人state、gripper及三视角RGB hash全部复现。不可把存储冗余误当152维模型状态；模型状态是原getter口径76维。未修改原数据，也未使用未来state。

## 当前下一步和禁止范围

F1/F4本轮有限9条任务已经完成，不要重跑、重复采纳或重新索取同一许可。

接下来应集中到此前最新外审的两条条件工作线：

1. F2：C/U/D在K0 limits-only、K1 +self、K2 +audited-world下分解固定终点失败；冻结seed/iteration/目标变换，最多15 IK+4轨迹query、2 planner-only scene、0物理。碰撞关闭解绝不执行，不再任意hub扫描；失败后只做一个版本化layout/grasp修订提案。
2. F3：实际开爪qpos与planner锁定状态、table/pad/bottle及相关机器人几何、统一world→planner变换、真正solver/worker world更新和known-clear/failed/endpoint审计。仅原r3063/r1401，满足前置条件才执行有限pregrasp/grasp/close/25mm lift；无shared-V/no-suffix/root/trainingraw扩展。

仍禁止Stage0重跑；Stage1/formal360/训练/H-reveal/compression/π0.5不因本轮成功自动获批。本轮成功是数据构造/realization基础设施和物理验收证据，不是Temporal Identifiability Gate或任何学习机制已成立。

## 机器证据入口

- `REALIZATION_NINE_COMPLETED_PUBLICATION_V1_20260906.json`：完整终端、Guard、POST_CHILD和所有新输出文件hash。
- `REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json`：9新+9原r_pc的独立raw/video复核、三个6-cell矩阵、F4跨realization等价。
- `STAGE1_READINESS_AFTER_NINE_REALIZATIONS_20260906.{json,md}`：统一计数及授权边界。
- `REALIZATION_UTF8_FAILURE_RESOLUTION_PUBLICATION_V1_20260906.json`、`REALIZATION_UTF8_TRACE_RECONCILIATION_V1_20260905.json`：原失败和CPU重建全部来源。
- `REALIZATION_CURRENT_STORAGE_LAYOUT_AUDIT_V1_20260906.json`：current数据的可复现无损解码。
- 活跃日志§475–§483：本轮直接用户许可、失败、恢复、全部真实结果与清理。
