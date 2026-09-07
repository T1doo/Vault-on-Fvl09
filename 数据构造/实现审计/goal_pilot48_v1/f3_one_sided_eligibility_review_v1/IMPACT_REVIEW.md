# V1正间隙上界失败：one-sided卸载模型适用性审查

状态：独立CPU分析/提案，尚未新schema实现、签发或GPU。V1/v5/issuer和该次失败文件均不修改。

## 全部失败条件定位

`analyze.py`读取实际tangent_certificate_candidate.json，重新运行冻结V1 validator；以私有AST仅把最终and表达式展开为逐谓词结果，未改其判断。self-hash、旧支持整体predicate失败且计数保真、实际scene/job/qpos/pose、250Hz与250连续帧、双指250/250/信号/原漂移/无禁止碰撞、table/其它支持0、同pad16帧真实支持、full single/batch world-collision、7负间隙仅attached瓶/pad、固定25mm目标等全部通过。

**唯一失败**是 `(abs(gap) <= 0.0001).all()`：仅hold index48、49、50三帧的正间隙超过100µm，最大+108.820525µm。全窗最小−0.073632µm，旧负向数值下界完全通过。分析receipt `ad5cf65cd5dd83a3c099e7ae673fb6c2144e734793c4cbd4d7a5e81b8e8e0b28`，逐项证据在analysis.json。

这不构成当前V1通过：已冻结的对称门确实失败，应保留为model-eligibility revision1终端，不能改成成功或重发相同manifest。

## 正向上界的问题及建议

V1的±100µm门把“近切触”定义成对称距离区域。负方向能表达native物体深入支撑面风险；正方向却意味着离开支撑面，是拟授权向上escape的安全方向。在该例中positive108.8µm没有引入新的native瓶-pad穿透，而planner仍因同一pair的附着球近似重叠拒绝。简单把100改成120µm只是按一次结果调数，缺乏一般安全意义，应禁止。

可审查一个独立schema `stable_grasp_one_sided_native_unloading_escape_v2`：不用任意正向近切触上界，改为全窗 **g_i >= −epsilon**，epsilon仍为原native数值精度0.1mm；只取消不安全性方向错误的正上界，不增加负向穿透容许量。

其适用区域不能仅靠这条单侧条件限定，必须同时保留如下完整证据链：

- 同一250帧真实稳定双指抓持/完整信号/forbidden0、原相对5mm/.05rad，不减帧、不换baseline；同pad至少一次原classifier真实支持、table/其它支持0。旧supported_hold完整predicate实际重跑并保留False，不伪造16→250。
- 当前实际full single/batch必须仍因world collision拒绝，且当前全部负sphere严格只属于attached瓶↔该hash绑定pad。这个真实同pair重叠而非任意正向阈值限定了模型差异的相关性。若已经真正远离且fullworld有效，根本不需要例外，应走完整world；不能套one-sided证书。
- actual scene identity、命名qpos、actor/EEF/抓持变换、native几何、robot配置与实际world都绑定；factory在任何CUDA构造前复核world/config，执行前复核几何和实际状态。不能靠放大球、增buffer或错误坐标制造“还在重叠”。
- 每次只允许从该actual postclose固定向上25mm目标，原native计划所有控制点不深入、下包络不下降、最终离开pad、计划actor rise≥原20mm；保留native fl3/fl5执行前检查、完整机器人/对臂/table/其它world约束。
- 证书只可用于这个单plan/单scene；结束或失败过期，恢复完整attached world的两路实际状态。原postlift20mm/5mm/.05rad/50帧及2fresh成功要求完全不改；不能把模型certificate当physical pass。

结论是“可形成更有安全方向依据的新model-eligibility设计”，不是当前已证安全或批准执行。更大正间隙仅在完整证据链仍真实成立时才可判适用，不能独立说任意正间隙都安全。

## 新版本反例与回归需求

1. 固定真实001输入：V1仍False；新V2若实现，只有正上界不再参与，必须记录原V1失败且所有其它条件逐一保真。
2. 正向gap从100→108.8µm且所有其它真实条件不变，应不因正向距离单独拒绝；同样的负向−108.8µm必须拒绝，不能把对称epsilon一起放大。
3. native负向深陷、任一控制点比原下包络更深、先下压后抬、最终不离支撑：拒绝，即使所有正向距离满足。
4. 正向gap明显大且当前fullworld已经有效/负pair为空：拒绝此例外，不伪造overlap去匹配。若唯一下游需求是完整world规划，则另走已验证完整world，不混入本证书。
5. 当前world另有robot/pad、table、对臂或其它负pair：拒绝，不能只筛出那7个可解释负pair并漏掉其它。
6. 支持全部来自table、同pad从未实际接触、双指断联、夹持漂移超原限值、contact信号缺失、时间/scene/hash/实际抓持变换不一致：拒绝。
7. 改buffer、模型球/质量/摩擦、拿历史scene/manifest绑定现计划，或复用一次plan证书：拒绝，不借新schema修改物理与预算。
8. 全部离散native检查通过而实际tracking/滑动导致postlift失败：物理门仍失败；不把离散规划证据升级为连续/稳定抓持证明。

## 版本与授权边界

- 已消费：model-eligibility revision1（tangent V1），本次保留失败。
- 拟新建：model-eligibility revision2（one-sided V2），目前**仅提案**，应有独立source/schema/测试/影响决策/manifest与预算，不重用revision1作业。
- 不变：稳定grasp recipe revision3、pregrasp route revision2、25mm lift、物理参数/全部实际verifier与两次fresh成功要求。不是第四次稳定配方，也不重置任何历史失败计数。
- Goal允许证据支持的pair/phase模型修订，但主调度仍须明确采纳这个新设计后才实现/签发；不能从本分析自行推定提高epsilon或GPU授权。Stage0、formal、训练等边界不变。
