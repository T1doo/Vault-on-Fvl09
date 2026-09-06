# 四族贯通与48条pilot输入持续Goal

完整授权/任务书：USER_GOAL_SOURCE.md。已知基线2b43b541c3ae8d9b1d8a8f396225dc50601786ec；历史已消费作业与失败不复活。所有新子作业标记ISSUED_UNDER_USER_GOAL，非独立GPT外审。

## 完成条件（全部须证据支持）

- F1–F4真实完整三分支采集能力。
- 8个pilot根/48格：每族A=3r_pc+3r_inv_path，B=3r_pc+3r_inv_motion；通过复核的已有18格显式复用，不重采。
- 逐格raw/trace/MP4/current/anchor/prefix/真实realization/原family verifier/计数/cleanup独立验收；F3/F4顺序及终态等价。
- 至少连续六条真实采集覆盖两个family、同一冻结版本集合，中途不改代码/目标规则/verifier；预留F2-A三path与F3-A三path作为首选连续队列，须在采集前冻结具体任务。
- 无训练的结构、负例、泄漏字段及时间对齐检查；正式40primary+16reserve、split、生成器、预算与执行方案草案。
- FINAL_REPORT逐条映射上述证据，不能把计划/CPU/单次规划当整体完成。

## 新Goal授权与不变底线

允许在总预算内自主修复、版本化重试、F3 micro→sharedV→replay→root、F2新布局三关系root、F4-B、path/motion与pilot输入登记；每类确定失败最多3个有证据、预先冻结的修订。F3研发确认改为同一冻结recipe在2个fresh scene真实通过微门；不同资产多样性单列，不阻塞该recipe开发。

禁止重开Stage0、伪造数据、物理weld、改family科学定义、事后放宽verifier/物理/事件/终态阈值。正式360执行、训练、H-reveal、compression、pi0.5仍不授权。pilot输入48/48不等于整个Stage1科学Gate通过。

## 总预算与调度

solver problems6000 / fresh scenes240 / robot-action scenes120 / full-trajectory collection attempts96 / GPU lease86400秒 / 同时1张GPU。所有新job预留最坏上限后启动；失败计账，未知保留unknown并暂停GPU。FK/碰撞/模型构造单列。模型dummy warmup不承担任务目标，将在Goal独立初始化策略中跳过并显式记录，真实规划cold初始化；不得隐藏实际任务solver calls。

GPU0–7任一实时fresh-idle卡，single-wave+原子Guard/UUID/lease/pre/post/ownership cleanup。主调度/root唯一可写总账和启动GPU；子代理仅独立CPU工作。每次真实budget模型按batch目标N计数、跨trace reset单调累计。

## 检查点

STATE.json / budget_ledger.jsonl / attempts.jsonl / pilot_cells.json / FINAL_REPORT.md（最终完成前仅草案）。账本初始消耗只统计本新Goal；历史2b43b54以前所有失败保留为baseline证据，不虚报新Goal消耗也不删除旧分母。会话重启不能重新初始化已存在总账。
