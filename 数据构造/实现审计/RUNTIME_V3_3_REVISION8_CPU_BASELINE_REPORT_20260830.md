# runtime-v3_3 revision-8 CPU baseline

R8严格依据r7 evidence：F2只用固定XY-only inside target0并保存普通planner-false输入；F3新增signed separation/shape identity并把preopen、disengagement、selected/full-assembly +250 no-recontact统一到fail-closed physical-contact signal；F4 staged/full统一使用已通过A-micro同源的top-down七段block carry。

科学设计、对象、arm、layout、F2 desired target/on/beside/final verifier、F3 V/H/program/10mm geometry与所有阈值、F4 common-X/slot mapping/ABC-ACB-BAC/final verifier均未改变。

```text
active tests = 412/412
snapshot tests = 412/412
diff = zero
source = 4b5ac619c0d765024bc7cdc01ea02e2a30e7a9bc195274961c626aa48f0c2d21
budget = bd62453d41b214a54eea045a9b9d6f641c8802cf2f384143a9e7b71d7e61b14a
parent = 441087839708ea2e12c8c3e44684f27d031b873645825d8963857649bd78ea82
```

F2/F3/F4独立P0审计通过。F3 shape identity真实pybind wrapper可用性仍需首个real receipt验证，但任何不一致都会fail closed。报告只允许exact-scope nonformal bundles，Stage0继续禁止。
