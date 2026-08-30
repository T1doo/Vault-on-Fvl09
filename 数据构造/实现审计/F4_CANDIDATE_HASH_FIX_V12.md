# F4 fresh-scene candidate hash fix v12

v3_4_1的F4在第一次corridor query前比较了fresh scenes的未规范化raw pose JSON hash。即使same-current/anchor已在`1e-6`级容差内等价，任何非零浮点差异都会使raw hash改变，从而把物理等价误判为candidate漂移。

v12冻结的语义身份是：

- candidate ID、priority、ordered segment IDs、release/neutral indices完全一致；
- right arm、layout、release target semantics不变；
- 每个target position误差≤`1e-5m`，quaternion使用sign-invariant angular error≤`1e-5rad`；
- raw pose hash仍保存为diagnostic，但不再定义语义身份；
- planner使用fresh scene实际重延且通过容差Gate的target，不强行回放另一scene的raw floats。

这是collector/infrastructure fix，不改F4 common-X、ABC/ACB/BAC、视觉slot、右臂、tray、release target或verifier。
