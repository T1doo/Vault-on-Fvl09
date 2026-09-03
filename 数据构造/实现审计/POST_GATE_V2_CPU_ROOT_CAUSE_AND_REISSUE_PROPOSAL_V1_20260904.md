# Post-Gate V2 CPU root cause and reissue proposal V1

日期：2026-09-04
状态：`PROPOSAL_ONLY_NOT_AUTHORIZATION`

## F2：不再是抓取问题

F2的exact top-contact prefix已真实通过，三个suffix replay的same-current/anchor/prefix physical acceptance也全过。瓶颈已定位到suffix首段：

| Program | Prefix-end EEF xyz (m) | First target xyz (m) | Result |
|---|---|---|---|
| inside | `[-0.280,0.040,1.050]` | `[-0.149,-0.200,0.906]` | `IK_FAIL` |
| on | `[-0.280,0.040,1.050]` | `[-0.115,-0.200,1.071]` | pass，后续4/4全过 |
| beside | `[-0.280,0.040,1.050]` | `[-0.039,0.080,1.050]` | `IK_FAIL` |

Inside与已通过on的水平位移接近，但inside首段同时下降约144mm；下一提案是保留原release target/verifier，只在其前派生一个同xy、z不低于prefix-end的carry waypoint，先水平转移再下降。Beside当前硬编码使用candidate0 `[0.20,0.12]`；冻结布局中candidate2 `[0.08,0.07]`同样满足beside半径/互斥条件，且使左臂路径不再越过桌面右侧。

这两个改动属于suffix route/candidate变更，未获授权。建议下一步只批准planner-only same-prefix suffix Gate：复用已封存prefix-end qpos，对inside新carry waypoint与beside candidate2各做一次精确链规划，不做branch physical/raw/video。

## F3：零scene wiring failure的精确修复提案

失败runner加载的是一个outer wrapper；真实helpers在`outer.base`。新proposal-only overlay只将运行时全局`base`从outer wrapper切换为已哈希绑定的inner base runner，不改tuple、scene、planner、budget或verifier。

CPU preflight必须证明`adapter_for/opened_scene/prepare_f3_scene/record_physical_scene/write_new`五个helper全部为callable，且scene/GPU/execution authorization均false。这只是对零消耗wiring failure的reissue提案，不是retry授权。

## F4

F4按最后外审已永久关闭。不请求任何reopen或新GPU操作。
