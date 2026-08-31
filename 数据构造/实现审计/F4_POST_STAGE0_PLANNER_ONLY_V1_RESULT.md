# F4 post-Stage-0 planner-only v1 result

状态：`FAILED_INFRASTRUCTURE_WITH_EVIDENCE`。

新layout canonical common-X→tray prefix reference完成并通过，计数为10 planner / 1 prefix execution / 0 recovery。第一个fresh `F4-ABC` scene在任何suffix planner query前终止：`derive_role_corridor_v11`的成功接口包含`preplanner_gate.pass=true`但历史上不提供顶层`pass`；新caller错误要求`derived.get("pass") is True`，产生`F4 post-Stage-0 A corridor derivation failed`。CPU复现确认exact candidate preplanner Gate本身全true。

因此本run没有提供新layout endpoint IK或三程序planner evidence，suffix execution/release均为0，不开放development root。Outer receipt随后因隔离HOME的ASCII locale无法编码中文traceback而成为0字节，是第二个infrastructure缺口。

运行在physical GPU0 / `GPU-2c620e6c-9639-2022-b573-9847dfa33769`；admission/launch为14 MiB/0%/P8/无compute。Child PID 475965退出且task-owned orphan=0，source-lock、job-cache、lease均通过；但postcheck时外部PID 475375新占用GPU0，Guard无法证明回到原基线并终止为`failed_cleanup_uncertain`。该外部进程未被干预。按single-use/no-retry合同不修后重跑。
