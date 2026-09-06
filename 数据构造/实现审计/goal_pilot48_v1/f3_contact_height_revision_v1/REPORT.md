# 唯一 revision2：grasp/pregrasp 同升10mm

`recipe.json`：`f3-r3063-com-contact-height-plus10mm-v2`，父为已实际执行的COM-station recipe，旧源和旧失败均保留。仅世界Z +0.010m；XY、朝向、站点、pregrasp间距、close、hold、lift、速度、物理参数和Gate不变。不得自动扫第二个高度。

CPU必要条件通过：五档闭合的实际native mesh掌/桌/pad检查、双指同原生瓶体片、两内表面同截面及原Robot入口转换往返。详细结果在 `closure.json`、`inner.json`，摘要 `cpu_audit.json`。新scene/IK/physical均0。

重要边界：这些检查只证明几何可达，不证明实测接触已经上移。闭合比例0.5时见证高度最高约0.7830m，仍可能略低于已知COM约0.7835m；0.75/1.0存在两侧COM上方的见证点（约0.7982/0.8007m），但那是静态重叠闭合样本，不保证物理会闭到那里。实际瓶体会阻止夹爪继续闭合，故不能把所有闭合样本视为真实可达状态。

下一fresh trace必须测量真实接触点相对COM的高度、法向/接触线与漂移，再走原postlift Gate。若仍只接触下半截，就保留这项失败，不能用本CPU pass宣称“上半截已抓稳”。此revision是有依据且必要几何合格的一次验证，不是已证成功。

CPU execution完成exit0，无恢复/重试或共享runtime编辑。recipe receipt `3b92578530147c0bd2000616a4e27306615c6df40ef75e15ec3795e285c9a1d3`；audit receipt `9a6fbf52e5da9496f94915c363b4b08c6937590e8f1b150a4e13b4b469765244`。
