# Stage 0 readiness：runtime-v3_3 CPU current

## BLOCKED_WITH_REASONS

CPU/static基线已经通过，但目前仍不能启动Stage 0：runtime-v3_3尚未运行真实SAPIEN/GPU scope，F1–F4 accepted real roots仍为0。

已经具备的部分：

- canonical prefix单次生成与三fresh exact replay代码；
- frozen suffix planner/execution接口；
- current/anchor、raw、verifier、cleanup与3/3 root finalizer；
- F1公平planner evidence、F2动态inside与互斥layout、F3 shared-V物理Gate、F4 no-action IK与staged blocks；
- 与冻结JSON一致的有限预算及one-shot/revision/GPU guard链；
- active和byte-equal snapshot各`243/243 tests passed`。

仍缺的真实证据：

```text
canonical-prefix real smoke
F4 A/B/C no-action right-arm IK
F1 accepted root
F2 accepted root
F3 accepted root
F4 staged A/B/C/AB Gate + accepted root
```

当前计数：Stage 0=0、Stage 1=0、formal F1–F4=0；没有训练、H-reveal、compression或π0.5。

下一步只能先发布CPU baseline v1.2，再按fresh source lock和≤1h one-shot authorization逐scope执行有限nonformal验证。四个family全部accepted以前，不生成Stage 0 manifest/budget/request。

补充：prefix-smoke run1/run2均在GPU0 busy时保持未消费，随后两轮source hardening使其source lock失效，现均明确superseded。任何真实launch必须使用v1.2 baseline之后生成的全新run3 source-lock/request/authorization。

Run3现已按v1.2 source签发且未消费，但21:45即时precheck仍显示GPU0被外部进程占用，因此`new_gpu_launch_authorized=false`表示当前设备admission失败，不表示没有parent/one-shot授权。GPU0 fresh-idle后仍须由Guard再次现场复核。

截至22:08，同一外部PID已连续三个goal turns阻塞GPU0；当前执行目标正式标记`blocked_external_gpu0_busy`。这不改变科学readiness=`BLOCKED_WITH_REASONS`，也不消费run3预算。
