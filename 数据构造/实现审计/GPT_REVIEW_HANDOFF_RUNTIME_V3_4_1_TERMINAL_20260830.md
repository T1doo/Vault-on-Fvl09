# 给 GPT 的 runtime-v3_4_1 终端审阅交接

请以本文、`RUNTIME_V3_4_1_POSTMORTEM_HARDENING_REPORT_20260830.{md,json}`、四个family manifest、receipt reconciliation、GPU scheduling audit、current registry/readiness 与代码快照为主要审阅入口。

## 请先看结论

`BLOCKED_WITH_REASONS`，不批准Stage0。

CPU hardening已真实完成：active/snapshot各461/461 tests、151/151 compile、byte-equal，source=`81c86036•120ffc`。本v3_4_1没有修改frozen scientific design，没有第二次source freeze或自动retry。

真实GPU0 targeted结果：

1. **F1 pass**：3/3 accepted，root finalizer accepted，46/3/0，shared executed-prefix hash相同。这是回归，accepted root increment=0。
2. **F2 fail**：EntryV11与ReleaseSafetyV10 pass，full-open和exact250帧成功，但FinalInsideV10的true-cavity/exclusive inside fail，22/1/0，所以不开full root。
3. **F3 fail**：canonical IDs正确，但canonical prefix在pre-shared-V抓取/接触/离桌Gate失败，7/0/0，三context未执行，不开full root。
4. **F4 infra fail**：pristine/prefix pass，但fresh candidate的exact application hash在第一次corridor query前不同，10/0/0。因为0个corridor被真正query，不能claim corridor/layout infeasible，A/B/C/full都没开。

四个scope均在physical GPU0串行，每项pre/post都P8/14MiB/0%/无compute，source-lock pass、timeout=0、orphan=0。

当前accepted roots仍1/4；Stage0/1/formal trajectory=0；`H_reveal=null`；无training/compression/π0.5。由于4/4未通过，本轮没有生成`STAGE0_USER_APPROVAL_REQUEST_RUNTIME_V3_4_1`。

请审阅的重点是：

- F2的final true-cavity失败是否需要新layout/physics impact review；
- F3的冻结grasp在pre-V前即不稳定，下一版是否必须升级grasp contract；
- F4的candidate hash应该绑定设计规范/quantized deterministic pose，还是应在同spec fresh scene中比较容差；本v3_4_1没有权限修。

本次请只做方向审阅，不要把上述终端失败解读成Stage0授权。
