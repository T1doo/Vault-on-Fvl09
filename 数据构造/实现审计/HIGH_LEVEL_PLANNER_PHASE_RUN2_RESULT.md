# High-Level Planner Phase Run2 Result

状态：`PLANNER_PHASE_COMPLETED_WITH_F2_AND_F4_PASSES_F3_EXHAUSTED`。

- 执行候选job：22（F2=12、F3=8、F4=2）。
- Fresh scenes：22。
- Planner queries：102。
- Physical executions：0。
- 新trajectory：0。
- 全部Guard task-owned cleanup pass，orphan=0，selected GPU均返回idle baseline。

## F2

- Planner-pass：`f2-inside-hv1-r09`、`f2-inside-hv1-r10`。
- r01/r02：pregrasp/grasp/lift pass，inside preplace fail。
- r03–r08/r11/r12：fresh runtime strict geometry 与CPU cavity证书不一致，在control chain前终止。
- Physical selection receipt：`9f64eb7a44c7fa0ef767c06777fbef79c533ee35a14c8d931fc35c794032d7b2`。

## F3

- 8/8 tuple 均在 `f3_level1_pregrasp` planner 失败。
- Level-2 selection为空，不运行物理资格或3-scene confirmation。
- Selection receipt：`acf74d004190a37830719d79f5c406b261ec446e0da9bf3a711ffadc12e8e5c7`。

## F4

- r01 的 A/B/C 共15段全部planner pass，为最低rank pass，冻结为Stage-A source/grasp template。
- r03 因并行审批竞态在r02被拒绝前已启动；它也通过，但只作冗余证据，不改变r01选择。
- r02/r04–r08不再运行。
- Selection receipt：`95668c8150c97ea188b13dfb57caff608b5af292860fc0b9d1df626cc63a9acb`。

统一machine report payload：`f9182418879566dc5d2072a54a7efd328623818a820cfb69a9873317fc88423f`。Stage1/formal360/training/H-reveal/compression/π0.5 仍未授权。
