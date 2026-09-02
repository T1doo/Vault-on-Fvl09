# V2.3.1 Smoke Activation Bridge Contract

状态：`CPU_SOURCE_IMPLEMENTED_AND_VERIFIED_AWAITING_SMOKE_APPROVAL`。

- Frozen Vault HEAD：`092638dfba73c7ad70ec4f8a5b7bd1fe14c1fff9`
- Implementation source：`d5b3a2d1d88e89caa7e5f020b8eab6feaaa20e48ce13765f1d08828b9c5496f0`
- RoboTwin tracked HEAD：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- Contract：`14c894e1130ed4d5d0ce707ec72c36fc79bea009ae83ed6fcec92aa5702c9e2b`

四类job仅允许`F2_STAGE_A`、`F3_STAGE_A`、`F3_STAGE_B`和`F4_PROGRAM`，必须经过wave issuer、完整authorization loader、GPU Guard binding、精确child dispatcher、production scene bridge、exact family runner和terminal receipt。禁止回退到`HighLevelPlannerRunnerV1`。

F3-B必须读取不可变Stage-A artifact registry。Planner seed必须从authorization贯通到job spec、`_planner_reset`和terminal。F4预算固定为target construction 12 + chain 30 = 42 queries/program；budget/hash/Guard/scene/dependency/cleanup错误属于`INFRASTRUCTURE_ERROR`并停止wave，普通planner Fail/IK_FAIL才属于`PLANNER_CANDIDATE_FAIL`。

本contract不是批准：wave approval、planner/GPU/physical/Stage1/formal360/training均为false。
