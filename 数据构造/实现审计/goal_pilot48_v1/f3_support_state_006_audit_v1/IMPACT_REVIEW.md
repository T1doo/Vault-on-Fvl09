# 独立“夹持稳定、native切触卸载、仅向上退出”模型certificate审查

状态：设计分析，未实现/签发/执行。它不是旧supported-hold的通过，也不能替换原物理门。

## 已有失败事实与可审查范围

006的原supported证据仍为pad16/250、旧bind_exact_pad失败；真实双指250/250、相对漂移0.072mm/0.00065rad、native最低点在pad±约36µm且无table支持。附着球仍有7处pad负间隙，最深−4.505mm。现有证据支持“近切触卸载的稳定夹持”，不支持“250帧连续支持”，亦不支持“完全off-support且fullmodel已有效”。

Goal提供有证据的pair/phase模型修订空间，但不允许改family/实际verifier/物理参数或把失败改写为通过。因此可审查的是新版本planner近支撑退出证书，而不是降低support_contact_frames门。应另立proposal/version/hash，并在主调度确认属于Goal允许的模型/phase修订后签发独立budget。此文不能自发扩展授权。

## 新certificate建议（与旧schema互斥）

1. 新类型 `stable_grasp_native_tangent_unloading_escape_v1`，明确记录旧supported_hold_pass=false、真实support_frames=16等原始计数。不生成伪造250；旧verify_support_witness/bind_exact_pad保持原样且继续拒绝该样本。不得 monkeypatch 旧predicate 返回True，也不得复制旧成功witness。
2. 精确同一fresh scene末250帧、命名机器人/瓶/pad、actual qpos/EEF/pose、native形状和时间戳全部hash绑定。双指接触250/250、原信号完整/禁止碰撞=0、原5mm/0.05rad抓持稳定性限值必须通过。支持变化单独记，不能删掉有支持的16帧或重设baseline。
3. 此证书限定**近切触卸载**：每一帧 native瓶最低点在同一pad顶面±既有native几何数值epsilon=0.1mm内；必须记录同pad至少一次原classifier真实支持、不得存在table/其它support真实接触或原禁止接触。该±epsilon仅延用数值几何审查精度，不是新的物理穿透容忍门。已有物理contact完整证据仍是必须项。若完全无pad证据或gap明显大于epsilon，不能借此证书；走另外的fullworld valid分支审查。
4. 创建模型前重新捕获actual世界和附着变换；实际single/batch原完整模型的当前状态、sphere分区/overlap与native归属必须审计。所有负间隙必须仅attached_bottle↔该hash绑定pad__0；robot↔pad/table和其它障碍/对臂、自碰约束完全不变。任何非此pair负间隙立即拒绝，不能因native瓶近切触就忽略整张pad。
5. 新policy需独立certificate validator及构造入口；可复用四类unswept/swept distance/collision的分区实现，但不能调用要求旧250支持的构造器时塞一份伪造witness。MotionGen构造前绑定callback，single/batch full/subset缓存、所有cost/constraint实际回调和分区hash均核验。除attached_bottle的指定pad pair外，所有sphere/障碍输出必须与fullworld一致。
6. 有效期只限一次原25mm向上退出计划。每个实际计划控制点用actual FK/附着变换重建native瓶；沿用原native不深入、下包络不下降、末端离支撑、actor计划升高≥20mm审查；此外核对它确为固定目标25mm、姿态不变、水平位置未人为改变。不是让任意横向carry/V也忽略pad。每段native fl3/fl5执行前Gate和原物理window照常。
7. 执行后仍用同一真实postclose baseline、原20mm/5mm/0.05rad/50帧postlift Gate。证书不让physical pass变真，不允许改变rise基准、时窗或阈值。退出完成立即恢复两路完整attached world，原pad重新参与所有附着球碰撞；未复核恢复前不得carry/shared V。仍须2fresh微门成功才能推进。

## 必须覆盖的反例

- table接触而pad未接触、仅通用support计数相同：拒绝。
- fake support_frames=250、使用旧成功ID或另场景trace：拒绝，不给旧predicate代签。
- 任一时刻双指断联、姿态漂移超原限值、signal缺失、臂/掌碰pad：拒绝。
- native深陷pad、gap超近切触区、pad identity不一致：拒绝，不能靠小球/换障碍名通过。
- 世界负间隙含fl_link或其他障碍、sphere名字/索引错配、仅替换单路solver回调：拒绝。
- 计划先下压后抬、横移摩擦推出、native旋转角使另一端更深、control为空/NaN：拒绝，即使最终高度合格。
- native离散点通过但物理tracking造成碰撞/滑动：原物理Gate仍拒绝；离散审查不升级为连续碰撞自由证明。
- 执行异常、证书过期、改变world/锁定关节/另一次plan继续用旧pair例外：失效；清理并记录原失败，不共享证书跨根/scene。

## 结论

该独立模型certificate有物理上合理的审查依据：planner球近似把触及支撑面的真实稳定抓持当作穿透，而实际正在卸载。它可以作为新有限实现/验证提案，但现在尚未证明安全接线或实际有效，不能放行006、不能修改旧supported门、不能从“允许模型修订”推出自动科学接受。

若主调度采纳，应先新命名空间CPU正负例/四入口mask梯度/单批callback/source/证书失效测试，再独立manifest的实际GPU验证；不能直接拿原006失败witness驱动旧factory。006与此审查的raw/native/hash证据均保留。
