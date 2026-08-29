# F2–F4 runtime-v3_3 revision-3 终止审计与 revision-4 impact review

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_3
formal_data: false
stage0_data: false
stage0_authorized: false
accepted_roots_after_r3: 1/4
```

## 总结

F2/F3/F4 revision-3 在 GPU4/5/6 并行运行后均被严格Gate受控终止。三张卡全部回到P8、12–14MiB、0%、无本任务compute；所有scene cleanup、monitor restoration、lease/cache、source-lock与orphan audit通过。没有r3轨迹进入Stage0或formal denominator。

## F2-r3

- task/physical 3/3与canonical prefix通过；prefix 1302 steps、planner19、selected contact fraction1.0。
- center-aware inside route 3/3 planner通过，on route 4/4通过；两者未执行，不能称语义成功。
- beside六个固定candidate全部失败：三项在source-high失败，三项在midpoint-high失败；总beside queries=9，root planner35、execution0。
- 根因修正：r3把planned spawn actor z=0.79误称table support z；真实settle z=0.740628，center-aware support target约0.740718，导致release/preplace整体高约49.3mm。
- 同layout历史accepted证据支持唯一safe sector：stand-relative `(-0.15,-0.04)`、world xy≈`(0.05,-0.07)`，不需移动stand。r4应使用真实support z和单一确定性route，不再搜索六候选。

## F3-r3

- task/physical 3/3通过；canonical reference完成8个official batch、pregrasp/grasp/close、两次4cm lift、clearance raise、2× same-height carry和50-step hold，planner14。
- 在shared-V开始前由`pre-shared-V stationary/grasp boundary Gate`终止；shared-V=0、suffix/branch execution=0。
- r3未在异常前保存partial trace或structured Gate receipt，因此八项predicate中究竟哪项失败无法从现有证据恢复；任何具体归因均为推测。
- r4先保持r3动作不变，新增结构化Gate exception、partial trace与failure receipt；同run禁止自适应。根据一次证据完备诊断再做下一source-distinct physical repair，不放宽阈值。

## F4-r3

- common-X九段、2713-step semantic prefix、fresh replay与physical Gate全部通过。
- Gate-A的pregrasp/grasp/lift成功，新增`A_carry_mid`首端点失败；planner13=`common9+A4`，suffix execution0，B/C/AB与ABC/ACB/BAC均未启动。
- r2/r3的A前三目标相同，arm qpos除夹爪尾项外近乎一致；将140mm平移减半仍失败，说明同orientation midpoint不是解决办法。
- r4拟对A/B/C统一使用60° inward-tilted right-arm cube grasp/place transform，保持common-X、layout/tray、actor final targets、programs、midpoint和verifier不变；先保留CuRobo原始status side-channel，再走原staged→full流程。

## Claim boundary

- F1仍是唯一accepted nonformal root。
- F2 inside/on仅planner artifact成功；F3没有执行任何V；F4只有common-X prefix成功。
- r4属于source-distinct implementation/evidence impact addendum，不改变F1–F4科学设计。
- Stage0/1/formal=0；没有训练、H-reveal、compression或π0.5。

## Evidence

| Family | Namespace tree | Guard SHA-256 | Terminal receipt SHA-256 |
|---|---|---|---|
| F2 | `31f1ee80fda07e14c4b2c2a1d2b0baffc5de176cc8fb54fd96257fb4563609d2` | `99e63e6ae52ba4d8a7cde82dd6db9a754dfb329838713f0369f0ede929620063` | `a22ca2165576343ceab660adb21e4b7d848e61e492af78705eef2e835fcdaed8` |
| F3 | `46361ff2bf3b93643254ac6bba3edf25a5353f8190350117a91a24b698623d2b` | `16253e909182076eddea7fc4e97aa9a8cf486305aada47e7b54440c5ef0b5935` | `a9449d0712fa0bdc7b2bfa57d252fb4486956dcfc4df6c3382e6f38a915af437` |
| F4 | `ec97c47705fcf7826ab9af3c1c138cbb262f5ecd4e6fcea1bd71c75e49b88d33` | `ce91c387986bf179895435b5fe41b81d5a16c10258db2dfdaa0c022c1100b944` | `2cdf09600606c1aaf245d57ac4d15dd848a7a60e62cfefcbffea9d4d2dc9f04e` |

