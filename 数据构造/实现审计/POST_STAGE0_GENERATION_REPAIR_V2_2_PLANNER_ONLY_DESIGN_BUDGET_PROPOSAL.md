# Generation Repair V2.2 planner-only 设计与预算提案

状态：`PROPOSAL_ONLY_NOT_AUTHORIZED`。本文只供 senior/user 审阅，不是 authorization、issuer、Guard bundle 或运行命令。

## 提案范围

- F2：固定首个 CPU certificate pair，以双臂、16 contacts、两个预登记 rotation、零 axial offset、0.09 m pregrasp 构成 64-recipe panel；每 recipe 仅检查 pregrasp/grasp/25 mm micro-lift 三段，共最多 192 planner queries。planner-only 结果不能代替 post-lift physical Gate，因此不能让 F2 candidate-ready。
- F3：先用 `4 assets × 2 arms × 2 regions × 8 contacts`、固定 rotation 0 与 0.09 m pregrasp 的 128-recipe Stage-A panel，最多 384 queries；再对最多 16 个最低 rank Stage-A pass 做八段 Stage B，最多 128 queries。总计最多 512 queries、144 fresh/reconstructed scenes，不自动扩展到全部 3840 recipes。
- F4：穷举 8 个 hv2 candidates × 3 个程序顺序，每个顺序 30 段，最多 720 queries、24 个相互独立 fresh/reconstructed scenes。ABC 单独通过不能选中候选。

聚合上限为 1424 planner queries、232 fresh/reconstructed scenes、86400 秒。若以后获批，每次启动仍必须从 GPU0–7 中实时选一张独立 fresh-idle 卡，执行 Guard/UUID/lease/pre-post/cleanup，一卡一 job，root/scene job 不 shard。

Proposal payload SHA-256：`94aa2ad1c97416a9bfa5de62e8f5a528a75bae50242aec39e78203fdd573b982`。

当前 planner/GPU/physical/Stage 1 authorization 全部为 false。
