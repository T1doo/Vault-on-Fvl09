# A0 postmortem-validation 执行报告

## 裁决

```text
A0: PASSED_NONFORMAL_A0
Stage 0 readiness: BLOCKED_WITH_REASONS
F1–F4 action scopes: NOT RUN / NOT AUTHORIZED BY THIS RUN
Stage 0 authorized: false
```

本次只执行了共享对话 `https://chatgpt.com/s/t_6a92743292b481918785f884b7a72a19` 批准的全新 one-shot A0。旧 run1/run2 的授权、消费、guard、output 和失败证据没有复用或覆盖。

## 授权链

| Artifact | Hash |
|---|---|
| parent user authorization | `122896069bf65963fab872a068d00ac42286e8149703c75d5a3690954cd2b68e` |
| scope request | `d8368a2d6fc7996b24528eaccada4ded9bdd7b75c93938860b2ecdde8df8b938` |
| source lock | `528830926c454e5e8aac952d70b9a14469c49d4c4c7384657d2cdc0acc2d9193` |
| one-shot authorization | `7bd47f4259bf7e51d2c53900c440b12d0604a08d7bd451ae555d2d35adaf46bf` |
| authorization consumption | `0e6177cbaa66921250173189d5164a884742482facb224b5a7b81167fe0672ba` |

固定条件：F1、seed `20260829`、`A0_pristine + A0_fresh_1/2/3`、600秒、planner/control/post-setup physics上限均为0、max invocations=1、automatic retry=false、physical GPU0 only。

## 真实运行

```yaml
output_namespace: probe_outputs/nonformal_A0_F1_seed20260829_run3_postmortem_validation
status: passed_nonformal_A0
physical_gpu_index: 0
gpu_uuid: GPU-2c620e6c-9639-2022-b573-9847dfa33769
guard_precheck: P8 / 14 MiB / 0% / no compute process
child_exit_code: 0
timed_out: false
guard_elapsed_seconds: 119.6918215751648
scene_elapsed_seconds: 110.3634307384491
guard_orphan_process_count: 0
scene_orphan_process_count: 0
post_release_verified: true
independent_postcheck: P8 / 14 MiB / 0% / no compute process
```

四场景结果：

| Scene | Scene ID | Current hash | Anchor hash | Planner/control/physics | Cleanup |
|---|---|---|---|---|---|
| pristine | `f1-A0_pristine-v1_2-000001` | `10d9c15…271c8` | `0f8444b2…9540d` | `0/0/0` | pass |
| fresh1 | `f1-A0_fresh_1-v1_2-000002` | `10d9c15…271c8` | `0f8444b2…9540d` | `0/0/0` | pass |
| fresh2 | `f1-A0_fresh_2-v1_2-000003` | `10d9c15…271c8` | `0f8444b2…9540d` | `0/0/0` | pass |
| fresh3 | `f1-A0_fresh_3-v1_2-000004` | `10d9c15…271c8` | `0f8444b2…9540d` | `0/0/0` | pass |

完整current hash：`10d9c15aa3740cd1abc9cbb6f2d4d345dfd97f47e66d2119af3c00d5210271c8`。

完整physical anchor hash：`0f8444b2ffa243ed1a2bfd40e39ad047fe1fd1b05ce64664b1cc1c7bc2d9540d`。

每场 activity receipt 都确认：

```text
planner_query_delta = 0
planner_query_record_delta = 0
instrumented_planner_wrapper_delta = 0
native_planner_query_count_delta_if_available = 0
native_planner_record_delta_if_available = 0
controlled_action_delta = 0
instrumented_control_call_delta = 0
take_action_count_delta = 0
physics_step_delta = 0
```

Renderer update为2，只用于current图像捕获，独立记录且不属于controlled action或physics step。

## 独立验证

- active CPU tests：158/158 passed；
- byte-equal Vault snapshot tests：158/158 passed；
- active/snapshot source与tests：`diff -qr`零差异；
- parent/request/source-lock/authorization/consumption：均由current validator重新验证；
- 4个scene、16个current/anchor/activity/cleanup artifact：16/16重新SHA-256通过；
- 4个scene instance ID唯一；
- current hash种类=1，anchor hash种类=1；
- budget validator pass；
- guard/scene orphan=0；
- GPU0独立postcheck恢复P8/14 MiB/0%。

测试过程中第一次启动Vault snapshot suite漏设snapshot `PYTHONPATH`，产生23个loader import error；使用正确snapshot root重新运行后158/158通过。GPU outer command首行由`/bin/sh`解释时提示`source: not found`，但shell继续执行了后续atomic guard；没有启动第二份job，原guard独立完成、消费唯一授权并返回0。该调度信息不改变guard内部source-lock、fresh-idle、child、receipt和post-release证据。

## 当前边界

A0 pass只证明：同一个规范能在四个fresh SAPIEN scene中重建严格相同的模型可见current与等价physical anchor，并能在post-setup capture window内保持零planner、零controlled action、零physics step且安全cleanup。

它不证明：

- F1三分支可行；
- F2 inside/on/beside三分支可行；
- F3三个完整程序与return可行；
- F4 common-X与ABC/ACB/BAC可行；
- 真实root pipeline通过；
- Stage 0 ready或authorized。

本轮没有Stage 0、Stage 1、360条正式数据、训练、`H_reveal`、compression或π0.5。
