# Updated Planner Wiring Smoke V1 Proposal V2

状态：`PROPOSAL_ONLY_NOT_AUTHORIZED`。Payload SHA：`36b6bac57fb6c7cceb6f7fc35858c1cb25492cd2106b662d878a4a475d01b801`。

- F2：6 queries / 2 scenes
- F3：20 queries / up to 4 scenes
- F4：126 queries / up to 3 scenes（42/program）
- Aggregate：152 queries / 9 scenes / 16200 seconds
- Physical/trajectory：0/0

S1–S5 顺序执行；S6A/S6B、S7A/S7B 由磁盘 terminal 条件触发。Infrastructure error 停止全 wave；普通 planner candidate fail 保留证据，不现场改参数。本 proposal 不授权执行。
