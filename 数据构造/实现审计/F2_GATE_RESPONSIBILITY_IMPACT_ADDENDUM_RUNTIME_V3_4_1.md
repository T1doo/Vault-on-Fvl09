# F2 Gate responsibility impact addendum — runtime-v3_4_1

F2 仍固定 `071_can/base1 + left arm + plasticbox/base2` 的 inside 分支。`F2ReleaseSafetyGateV10` 与 `F2FinalInsideSuccessGateV10` 的源文件未改，SHA-256 仍为 `6a4910f6da4e6f90fb78083ff675b4ec5a3cfaf0b52fe29495958a7a449310c9`。

新增 `F2PreloadEntryEvidenceGateV11` 只负责在 partial-open 前确认 exact 10+50 帧、指定手指连续接触同一 can、无非预期接触、opening/rim≥20mm、contact/geometry 证据完整，以及动力学仍处于 v10 controller safety envelope（0.05 m/s, 1.0 rad/s）。旧 0.02 m/s / 0.05 rad/s 值只保留为 diagnostic，不再在 partial-open 前阻断。

唯一允许顺序为：

```text
EntryEvidenceV11 → partial-open → ReleaseSafetyV10
→ full-open → exactly 250 frames → FinalInsideSuccessV10
```

任何 evidence 缺失都是 infrastructure/schema failure。本改动不改 scene、object、arm、inside predicate、v10 safety/final threshold 或正式科学设计。
