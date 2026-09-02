# Full Planner Panel V1 Proposal

状态：`PROPOSAL_ONLY_NOT_AUTHORIZED`；只能在 wiring smoke 无基础设施错误并经再次审阅后考虑。

- F2：`64 × 3 = 192` queries。
- F3：Stage A `128 × 3 = 384`；最多16个 strata survivor执行 Stage B，`16 × 7 = 112`；F3最多496。
- F4：每个 rank 90 queries，第一个三程序完整 pass 后停止；最多720。
- 总上限：1408 planner queries。

三个 family 必须分别授权；同一 family 保持冻结顺序串行。所有 planner 结果只用于选择后续 physical probe，不自动改变 Stage 1 readiness。

Proposal payload：`0873f3050a1a294bb1b53d650f672164a71beb94665cb5f38c559d1a7546c9bd`。
