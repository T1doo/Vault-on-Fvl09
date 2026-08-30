# runtime-v3_3 revision-7 CPU baseline

Revision-7严格依据r6 immutable evidence：F2仅将inside首个EEF command替换为固定r6证据驱动的SE(3) compensation并记录diagnostic alignment；F3仅修projection consumer旧键、planner前partial evidence和implementation-error分类；F4仅修role-A pose provenance与既有`1e-10` nonzero-impulse接触语义。

对象、arm、layout、F2 desired actor target/on/beside/final verifier、F3 V/H与三program/10mm clearance、F4 +16mm targets/20mm micro/全部数值Gate均未改变。

```text
active tests = 382/382
snapshot tests = 382/382
diff = zero
source = 2ed82e7a5e6a2a03a3cf7b1cfb3dde82acba637f24c574c64c47099516ee72c8
budget = 1a3e2e18acc8af984dbb76e637ac140c930c332748202e7b61564b77c86f8d62
parent = dc16de4ddd05481160713f97182206d60e54acb8b8a67cc886659d19b77739e1
```

三组独立P0审计均通过。本报告只允许后续exact-scope nonformal bundle；physical GPU0–7中任一张卡仍需job启动前独立fresh-idle，Stage0继续禁止。
