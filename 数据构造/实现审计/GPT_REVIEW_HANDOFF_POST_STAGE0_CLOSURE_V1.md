# GPT Review Handoff — Post-Stage-0 Closure V1

## 已完成

- 第一批post-Stage-0 evidence已push至Vault main基线`b5fb066`。
- F2 replacement与Stage 0 terminal seal已核实完成，禁止重跑。
- F3CommonGraspPrefixV2与F4 derivation interface V2均完成CPU freeze、source lock、single-use authorization和唯一GPU run。
- Guard cleanup已改为task-owned cleanup / idle-baseline / external-arrival分账。

## 终端结果

- F3：V2 authorization已消费，但旧runner字段检查在0 planner/0 execution处阻断；没有物理结论，0/3，禁止retry，已生成task/asset redesign request。
- F4：真实进入IK；A前四段Success，A_preplace IK_FAIL；无完整route，禁止临时waypoint和A-only development，进入layout impact review。

## 下一会话先读

1. `POST_STAGE0_CLOSURE_V1_REPORT.md/json`
2. `POST_STAGE0_CLOSURE_V1_F3_RESULT.md/json`
3. `POST_STAGE0_CLOSURE_V1_F4_RESULT.md/json`
4. `POST_STAGE0_CLOSURE_V1_REGISTRY.md/json`
5. `F3_TASK_ASSET_REDESIGN_REQUEST_V1.md`
6. `正式数据构造日志.md` §221–§229

## 禁止

Stage 1、360 formal、训练、H-reveal、compression、π0.5；重跑已消费F3/F4 Closure authorizations；重开Stage 0；在F4增加临时waypoint。
