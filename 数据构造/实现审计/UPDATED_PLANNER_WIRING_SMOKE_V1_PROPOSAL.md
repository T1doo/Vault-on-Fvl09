# Updated Planner Wiring Smoke V1 Proposal

状态：`PROPOSAL_ONLY_NOT_AUTHORIZED`。Artifact SHA：`43c1f6331edd6b3beda6227a2ff84ce3411d8fa2865e43de80607f8278943a94`。

V2..3漏计了F4构造抓取目标时的planner调用。V2.3.1按每个role 4次batch query、三个role共12次，加30段program chain，固定为42 queries/program。

- Smoke：F2 6 + F3 20 + F4 126 = `152 queries`，最多9个fresh scene。
- Full panel：F2 192 + F3 496 + F4 1008 = `1696 queries`。
- S1–S5串行，任一`INFRASTRUCTURE_ERROR`停止wave。
- S6A/S6B仅在对应F3 Stage-A planner pass后签发。
- S7A仅在S3 pass后签发，S7B仅在S7A pass后签发。

本proposal不授权planner、GPU、physical、Stage1，也不允许自动进入full panel。
