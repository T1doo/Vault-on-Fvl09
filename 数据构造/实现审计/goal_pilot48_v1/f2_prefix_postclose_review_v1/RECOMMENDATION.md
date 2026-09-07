# F2 prefix001 postclose：独立CPU结论及有限建议

证据：`analysis.json`，receipt `fba75d02f6e47928b1f729380534ae8fba1be6984dc009196d5da41946acd99e`。
未修改旧source，未GPU、未reserve，未把旧partial trace当完整prefix。

## 实际状态

- table top：0.7400000095367432m。
- 初始native can gap：−1.444µm；postclose最后一行：**+0.298206mm**。
- 最后50帧gap为+0.251277～+0.298206mm，全部没有物理can/table接触；原V8 contact evidence完整。
- 双指真实接触50/50，最后10帧也是10/10；grasp相对平移漂移0.110247mm、角漂移2.221e−6rad。
- 最大线速度0.0018461m/s、角速度0.0013586rad/s；从初始到末帧总转角0.0019033rad。没有证据支持严重倾斜、穿透或抓持丢失。

因此这次不是底面穿透；夹持过程中罐体已微小离桌，绝对值support-band入口错误拒绝了正向离桌间隙。未执行12cm lift，仍不算prefix成功。

## 不能直接声称fullworld已可用

将以前F2的字面can-body碰撞球刚性变换到本次真实postclose EEF/can变换，CPU重算仍有 attached_can↔table__0 **−4.67286mm** 的球模型重叠，其余world最近间隙正值、无self重叠。
这不是新的GPU sphere fitting/kernel验证，不能冒充实际fullmodel判定；但它明确提示“native已离桌”不等于“带4mm padding的fullmodel能起步”。

## 建议一个F2自身的新模型适用性版本

不改原eps、不把0.1mm改成0.3/0.4mm、不导入F3 witness或授权、不改grasp/lift/物理阈值。

1. 从新场景实际postclose状态构建full single/batch模型，首先实测fullworld。若两路通过，直接用fullworld，禁止不必要的pair exception。
2. 若fullworld拒绝，仅在所有负world pair都明确属于attached_can↔table__0、native无深入且位于正确table footprint、真实抓持/identity完整稳定时，考虑**F2-specific nonpenetrating upward-lift clearance certificate**。
3. 该证书区分“实际桌面支撑”和“实际已离桌但padding重叠”，不再要求后者有table contact。负向数值下界仍原0.1mm；对正gap不引入任意扩大后的abs阈值。
4. 只允许原固定12cm向上lift；真实计划每个native样本不得比起点深入、下包络不下降、末端离台。机器人/table、其它障碍与self检查全部保持；执行后恢复fullworld，再走原prefix物理Gate。
5. 若出现其它负pair、未知身份/坐标/scale、native穿透、抓持证据不完整或pair模型仍拒绝，停止，不强行执行。

最小有限执行仍可保持一次新prefix namespace的3 MotionGen/1scene/1action/0collection；高层模型检查另记。若先用保存状态做零scene模型核对，必须有独立新job/计数，不能消费或重开prefix001。

本文件仅给出待审查的F2新版本建议，没有实现该适用性变更、签作业或执行lift。原inside参数化实现暂留，先解决这一prefix前置条件。
