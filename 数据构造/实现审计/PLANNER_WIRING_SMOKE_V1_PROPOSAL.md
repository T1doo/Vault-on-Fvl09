# Planner Wiring Smoke V1 Proposal

状态：`PROPOSAL_ONLY_NOT_AUTHORIZED`。

- F2：两个不同 arm recipe，2 scenes，6 planner queries。
- F3：两个不同 asset/arm 的 Stage A，共6 queries；仅 Stage-A pass 才进入7-query Stage B，最多14 queries；合计最多20 queries、4 scenes。
- F4：只从 `hv2-r01` 开始，按 `ABC → ACB → BAC` 条件顺序，最多90 queries、3 scenes。
- 总上限：116 planner queries、9 scenes、physical=0、trajectory=0。

若以后单独获批，首次 smoke 使用一张实时 fresh-idle GPU 串行执行；任一 infrastructure/source/Guard/cleanup 错误立即停止。结束后必须先发布 `PLANNER_WIRING_SMOKE_V1_TERMINAL` 与 `PLANNER_WIRING_SMOKE_V1_REVIEW`，不得在同一 authorization 下进入完整 panel。

Proposal payload：`2d93d86e351250f1c4866a84b8341fae5cc8b7ea078d2c790fc8e3bb9c440481`。
