# 数据构造进度：2026-09-05 F2 Run3 后

整体仍处于正式收集前的开发验证阶段。Stage 0保持封存；Stage 1尚未授权，formal为0 roots / 0 trajectories。

| Family | 已验证结果 | 尚需完成 |
|---|---|---|
| F1 | 5个development roots / 15条r_pc | r_inv_path/r_inv_motion设计、授权及验证 |
| F2 | Run3短TMPDIR实际生效；inside planner 5/5通过；beside目标绑定失败，0 beside queries | 对新目标计算差异做CPU审计；无第四次dispatch授权 |
| F3 | 旧三候选规划3/3、物理0/4；新full-window Gate 8/8测试，四旧trace逐帧回放全部提前拒绝；四新recipe SHA核对一致 | candidate-bound executor/Guard CPU接线、规则payload哈希核对、窄复审；GPU仍未授权 |
| F4 | V2.2 authority/held-flock/cooldown实现；7/7专测和真实持锁CPU生命周期通过；finalizer保持原字节 | 收口V2.2最终审阅包及新外审；GPU仍未授权 |

F2 Run3没有物理执行、raw或accepted root。inside规划通过仅证明该路线可规划。GPU4已通过Guard及外部postcheck释放到12MiB/0%/P8，任务进程无残留。beside scene的独立cleanup receipt未产出，终端发布明确保留此证据缺口。

当前开发验收数据仍只有F1的5 roots/15条r_pc；Stage-1-authorized计数0/48，formal计数0/40 roots、0/360条。此次新增检查通过不等于F2/F3/F4数据已经修复成功。

本轮证据入口：

- EXTERNAL_REVIEW_F2_RUN3_F3_WINDOW_F4_V2_2_20260905.md：已完整读取的20729字符外审正文。
- EXTERNAL_EXECUTION_DECISION_20260905_V1.json：结构化决定与授权边界。
- REVIEW_20260905_CPU_CHECKPOINT_V1.json：CPU实现和实际测试状态。
- F2_RUN3_TERMINAL_PUBLICATION_20260905.json：最新真实运行终端。
- F3_FULL_WINDOW_REPLAY_V1_1_20260905.json：完整窗口回放。
- F3_DETERMINISTIC_CANDIDATE_FREEZE_20260905_V1.json：四个新候选，非物理资格证明。
- F4_V2_2_LIFECYCLE_CPU_20260905.json：持锁生命周期测试。
