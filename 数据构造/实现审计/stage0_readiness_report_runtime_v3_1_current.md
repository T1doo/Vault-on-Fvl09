# Stage 0 readiness — runtime-v3_1 current

## BLOCKED_WITH_REASONS

Runtime-v3_1 已完成第五轮 GPU 前 CPU/code 加固。131/131 active/snapshot tests、76-file compile、import-side-effect audit 与 root-cpu9 synthetic evidence通过。A0 现在使用 post-setup activity monitor v2、orchestrator v1_2、real adapter/context v1_2、one-shot authorization v1_1 和 guard v2_1；代码、预算、family/seed/spec、output与单次消费均可机器核对。

## A0 用户审批 readiness

```text
a0_user_approval_readiness = READY_FOR_USER_REVIEW_BEFORE_A0
```

这只表示 A0 前的 CPU/code 工作与待审批材料已经齐全。`A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.json` 仍为 `approved=false / gpu_probe_authorized=false`；没有最终 authorization receipt，也没有运行 A0。

但以下事实仍阻止 GPU budget 和 Stage 0：

1. A0 已达到用户审阅条件，但尚未获得用户单次批准，也未运行；
2. concrete adapter/runner 尚无真实 SAPIEN/GPU evidence；
3. F1 真实 actual-prefix red/green/blue 3/3 未运行；
4. F2 six fresh planner variants/chained beside 未运行；
5. F3 V→H release diagnosis 未运行，完整三个程序仍 incomplete；
6. F4 common-X routes 未运行，A/B/C 与 ABC/ACB/BAC 仍 incomplete；
7. runtime-v3_1 budget仍 `proposed_for_user_review / approved=false / frozen=false`；
8. 不存在合法、未消费的 `cmf_runtime_v3_1_gpu_authorization_v1_1` receipt。

`H_reveal=null`；Stage 0/1/formal trajectories 均为 0；无训练、compression、π0.5。不得启动 Stage 0。
