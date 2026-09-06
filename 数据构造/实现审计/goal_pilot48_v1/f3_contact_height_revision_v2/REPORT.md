# 最后稳定修订3：总抓取高度+12mm，lift保持25mm

唯一recipe `f3-r3063-com-contact-height-plus12mm-v3` 已冻结：父为+10mm实际抓取recipe，仅grasp/pregrasp再同升2mm，原topdown总高度+12mm。station、朝向、close0.50、hold250、lift25、速度、质量/惯量/摩擦与所有Gate不变。稳定修订计数=3，禁止同类第四次变更，不扫其他高度。

五档native闭合/掌桌pad安全、双指同瓶片、同截面内表面以及原Robot入口roundtrip必要条件全部通过。与+10mm不同，在闭合比例0.5时，两指都已有COM上方见证：每侧2点、最高z−COMz=+1.410214mm；仍也有COM下方候选。比例0.75/1.0也有双侧上方点。**静态相交样本不是实际闭合轨迹或抗滚转证明**，真实接触线/COM与原postlift Gate仍须下一fresh trace，至少两次fresh成功。

路径保留004已成功低intermediate pregrasp Z=1.03357000698，再至新高pregrasp Z=1.04557000698。`route_spec.json`绑定004真实成功plan/window与新recipe ID。新增12mm段13个固定native开手几何采样及roundtrip全通过，不把手几何说成完整机器人IK或实际规划路径。

可直接复用已冻结 `f3_runtime_v3.micro.run`，不改其源：manifest的recipe_spec_path和route_spec_path指向本目录。4项新路径绑定的run生命周期CPU测试通过。执行最多4singlequery/1scene/1action，失败立即停止，无自动重试。当前没有GPU、manifest或真实物理执行，仅主线程可签发。

recipe继承的shift_rule/height_preserving_world_shift_m仅指父COM-station的XY平移，不代表总高度；unique_revision_delta=[0,0,.002]相对+10mm父recipe；总高度由total_height_delta_from_original_topdown_m=.012明确记录。执行仅使用desired实际poses，不再叠加delta。contact-height报告沿用旧schema名称revision2但数据/文件hash绑定本次revision3，schema标签不等于recipe计数。

CPU小型源码复制命令曾在print前误留一元+，打印后exit1，无目标文件写入；修正命令后经apply_patch建立新源，实际所有核验命令均exit0。旧文件与共享runtime不改。所有本目录产物已交付冻结。
