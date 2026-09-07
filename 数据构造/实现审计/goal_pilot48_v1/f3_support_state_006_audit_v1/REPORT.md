# 006 postclose：接触边界卸载，不满足原支持例外，也非全world可直接通过

原trace最后250帧逐帧重跑同一个物理contact classifier：pad支持16/250，table0/250，双指各250/250，信号完整，禁止碰撞0。hold相对漂移仅0.072053mm/0.00064946rad，稳定而非落台或明显滑脱。

但不能称整个hold已off-support：16帧仍存在真实pad接触。native瓶最低点仅在0.749999886–0.750035976m范围，最后0.750021154m，相对pad顶面仅约21微米；是近乎相切的轻微卸载，不是明确离台间隙。错误“table contact cannot replace pad support witness”只表示原250帧pad条件失败，本次没有任何table物理支持，不应按字面误报落台。

保存的actual postclose EEF、125个attached球和原4mm buffer字面重算：仍有7个球与pad负间隙，最小−4.504922mm；仅去掉buffer做诊断仍有2个球负间隙。没有改buffer，CPU重算也不是实际CUDA full-model validity检查。因此不能因为末帧没有pad impulse就绕过bind_exact_pad，亦不能宣称可用“完全off-support+fullworld valid”新分支直接lift。

结论：原支持例外所需250/250不满足；新的全离台且完整world有效条件也没有成立的证据，而且字面球重叠给出相反证据。保留006失败，不触发sharedV。若要制定“近支撑/卸载过渡”的新证据规则，这是单独模型例外设计审查，不能用修改计数、重置hold起点或伪造支持witness代替；本任务没有修改任何runtime/Gate/物理参数。

复现：`analyze.py`一次载入NPZ数组，原classifier处理250帧并输出analysis.json；`spheres.py`对保存球与native pad计算字面gap，输出sphere_overlap.json。均CPU-only、无Scene/solver/GPU。prefix_extension_v2仍暂停草案，7项CPU顺序/lifecycle测试通过不构成执行许可，也不覆盖当前support分支缺口。
