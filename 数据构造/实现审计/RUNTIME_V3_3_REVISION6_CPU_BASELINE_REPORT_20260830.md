# runtime-v3_3 revision-6 CPU baseline

Revision-6以r5真实证据为唯一修复依据：F2增加10帧warmup后复用原final50 Gate；F3使用target-quaternion-specific fl6/7/8 projection及fresh live model/support/link audit实现10mm compound clearance；F4统一将A/B/C top-down pregrasp+grasp上移16mm，micro保持20mm。

科学设计、对象、执行臂、V/H、program、布局、planner数量、verifier阈值与strict contact policy均未改变。

```text
active tests = 359/359
snapshot tests = 359/359
diff = zero
source = 3b771f97a5b2b53db53bf71ec9f1fe15727614a1303e2f415197e65655580a7d
budget = 9f0fb00bf7a9d1c4317be2233e53f18ee670c65b29eb08e56c7d7a5c3b9930cb
```

三组独立P0审计均通过。本报告只允许后续exact-scope nonformal bundle，不授权Stage0。
