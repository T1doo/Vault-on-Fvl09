# idea 主干：动作序列的（功能性意图）理解

> 整理日期：2026-07-26 ｜ 来源：public 仓库 [T1doo/T1doo-Research](https://github.com/T1doo/T1doo-Research)
> 主干出处：`前置论文/论文参考.md`（2026-07-11）+ 师哥原型图；当前定位以 `idea1-动作到功能性意图-重新评估与实施路线-2026-07-21.md` 为准。

---

## 1. 师哥原型（idea 的最初形态，2026-07-11）

![师哥idea原型](attachments/师哥idea原型-idea1动作序列的理解.png)

原型图转录（**idea1：动作序列的理解**）：

- **issues**：正常的训练模式是从视觉内容到动作，模型本身缺乏对动作含义的理解。
- **method**：通过 RoboTwin / LIBERO 的虚拟环境自动构建一个面向多物体操作的数据集，然后进行不同类型的操作，构建 `<视觉，动作，指令>` 标签。然后通过向 VLA 输入动作和视觉，预测该系列动作的目的。通过双向的"动作–指令"学习，强化模型的动作理解能力。
- **难点**：标签的设计可能要精细化一些，因为 action chunk 本身是短促的而不是一次性输出一长串动作。怎么让模型理解一个较长的动作，这是一个问题。（或者直接告诉模型一个比较长时间的累计变化？是否有效呢？）
- **关键词**：原子 VLA、CoT。

## 2. 师哥给的论文参考清单（`论文参考.md` 原文要点）

| 论文 | 角色 |
|---|---|
| π0.5 (arXiv:2504.16054) | **主要要使用的 backbone** |
| VLA-JEPA (arXiv:2602.10098) | 刚中 ECCV 的模板，可参考写作 |
| RoboTwin 2.0 (robotwin-platform.github.io) | 数据生成器 / benchmark |
| LIBERO (libero-project.github.io) | 数据 / 评测 benchmark |
| Motus (arXiv:2512.13030)、LingBot-VA (github.com/robbyant/lingbot-va)、FastWAM (arXiv:2603.16666) | 世界模型三篇 |
| 附加建议 | VLA-CoT 拓展阅读；理解 CoT 概念本身；π0 及该系列后续版本（0.6/0.7）也可看 |

各论文的压缩总结见 [相关论文速览](相关论文速览.md)。

---

## 3. idea 的两轮演进（衍生分析摘要，非主干本身）

### 3.1 第一轮（2026-07-11 立项报告）

- **动机成立**：现有 VLA 是"视觉→动作"的反射式映射，"会做 ≠ 理解"有实证（RoboSemanticBench：抓取成功但选语义正确物块近随机；LIBERO：语言嵌入 ≈ Task-ID；VLA-JEPA 自曝指令细粒度理解差）。
- **原始骨架已被占位**："双向 动作↔指令 + 反向动作→语言"——LACY (arXiv:2511.02239, ICRA'26) 已做 L2A+A2L+循环一致性；轨迹字幕也有前作。
- **当时的重定位**：不做"又一个双向 VLA"，做"**长时程动作序列的意图级理解**"——原子切分 + 累计 delta 把短 chunk 聚合成可被语言解释的意图，并把"理解"当评测终点、验证"理解→控制"因果。三点绑定：①意图级 > 动作描述级；②长时程/累计 delta；③理解作为评测终点。

### 3.2 第二轮（2026-07-21 重新评估，**当前版**）

新证据进一步压缩了创新空间，核心判断修订如下：

| 旧判断 | 新证据 | 现在的表述 |
|---|---|---|
| "动作→语言没人做" | LACY（双向+循环）、Anchor-Align（动作派生方向词联合训练） | 研究的是**长窗口、目标/功能层级、因果与歧义感知**，不是"首次动作→语言" |
| "轨迹目的总结是空白" | ProprioCaption 已做整轨迹目的总结（但规模小、无结构化真值） | 必须更结构化、可验证 |
| "语义世界模型可抢命名" | WLA 已预测 textual intention + dynamics | 强调**反向的、action-conditioned intent grounding** |
| "history intent 空白" | IntentVLA 用视觉历史做 short-horizon intent + AliasBench | 差异：显式语义目标、且是**动作→意图** |
| "语义辅助任务反哺控制即贡献" | Anchor-Align 已用低层方向词显著改善 OOD/控制 | 必须证明**功能性意图优于低层描述**，并配乱标签/等参数对照 |
| "π0.5 有 FAST 通道可小改" | 官方 openpi 的 π0.5 **只支持 flow head** | 需新增 observed-action encoder，不是改张 mask 的小事 |
| "累计 pose delta 是核心创新" | 同一累计位移可对应不同路径/目的 | delta 降级为**输入压缩/消融项**；核心是动作事件与谓词状态变化 |

**当前可防守的核心问题**（一句话）：

> 在**屏蔽任务指令和未来信息**的因果条件下，让 VLA 从一段**已执行动作**中识别"功能性意图/目标状态"，**显式处理共享前缀的不可识别性**，并验证这种长窗口、目标级 grounding 是否比低层动作描述、视觉捷径和普通辅助任务**更能改善 OOD/长时程控制**。

**术语分层**（不再混用宽泛的 A2I）：

- **A2G**：动作→目标状态谓词（第一阶段，可自动验证）；
- **A2Subgoal**：动作→已达成子目标；
- **A2FI**：动作→功能性意图（核心，L3 层级："拿起杯子，以便随后放入柜子"）；
- 语义层级 L0 连续动作 / L1 动作描述（LACY、Anchor-Align 已占，只做对照）/ L2 目标状态 / L3 功能性意图（核心）/ L4 任务级目的。

**歧义是研究对象而非噪声**：共享动作前缀（"抓起杯子"之后可能放柜子也可能放桌面）时标注候选意图集合而非强猜唯一标签；可定义"意图显现时刻 t*"（模型需要看到多少动作才足以区分意图）作为新指标。

**仍可能成立的空隙**（截至 2026-07-21 检索，无人同时做到）：①输入是已执行动作窗口；②输出是结构化目标/功能性意图；③显式处理共享前缀不可识别性；④用反捷径与受控协同训练检验"理解本身"及其对控制的因果作用。

---

## 4. 实施路线（07-21 版摘要）

```text
阶段 A（数据与诊断）：LIBERO replay → predicate/event trace → A2G 样本
  → 对照：visual-only / action-only / visual+action / shuffled-action
  → 动作是否提供额外目标信息（ΔA）？ 否→转诊断 benchmark；是→阶段 B
阶段 B（共享语义训练）：policy-only vs Anchor-Align-L1 vs probe-only vs shared-A2FI
阶段 C（控制与长时程）：LIBERO-Goal OOD → LIBERO-Long/PRO → RoboTwin/RMBench（可选）
```

- **防捷径纪律**：屏蔽原始任务指令、终态泄漏、任务 ID、未来动作、标签模板；主指标必须报**动作条件增益** ΔA = Score(V,S,A) − Score(V,S)。
- **架构要点**：π0.5 保留 flow 控制分支，另建 observed-action encoder → 共享 VLM adapter/LoRA → A2FI head；训练用交替多任务 batch；先写可见性矩阵与 mask/梯度单元测试再写模型。
- **短 chunk → 长窗口**：chunk 是控制/重规划单位，意图是语义单位；聚合**实际执行过**的动作流（不是拼接预测 chunk），按夹爪/接触/稳定谓词事件切段，短段编码 + 因果时序聚合；delta 分三层 Δpose/Δobject/Δpredicate，事件级 delta 序列优于单一首尾 delta。
- **决策闸门**：G0 标签质量（抽检 200 窗口）→ G1 动作条件增益 → G2 共享训练优于 probe/低层/等参对照 → G3 预注册控制主指标（3 seeds、最小效应量）。
- **时间线**（自 07-21 起四个月核心 + 一个月可选）：W1–2 定义与工程冻结（openpi/LIBERO commit、π0.5 推理跑通）→ W3–5 标签流水线（G0）→ W6–8 H2 最小诊断（G1）→ W9–12 协同训练（G2）→ W13–16 H1 控制实验（G3）→ W17–18 写作定叙事。
- **论文形态**：理想=方法论文；中等=理解方法+诊断 benchmark；H1 不成立→fallback 为"长时程动作理解诊断基准+数据集"（负结果也可发：揭示 trajectory-caption 类工作的场景捷径）。

## 5. 本地落地条件（fvl09 服务器 + 已配好的 RoboTwin 2 环境）

> 2026-07-26 补充。依据：工作区 `Robotwin2/` 已验证环境（配置详情见 `../Robotwin2环境配置/`）与本地数据实测。

### 5.1 算力现状与对骨干选型的约束

- fvl09 共 8× NVIDIA RTX 3090（24 GB，compute 8.6），驱动 535.247.01。**物理 GPU 2 已确认故障且短期不修**，项目激活脚本按稳定 UUID 默认屏蔽，实际可用 **7 张健康卡**（激活后逻辑索引 `cuda:0..6`）。
- 共享服务器纪律：每次实验前先只读检查占用、选空闲健康卡，不影响其他同学作业；RoboTwin 官方 `collect_data.sh` 内部 `export CUDA_VISIBLE_DEVICES=${gpu_id}` 用**物理索引**覆盖激活脚本的 UUID 屏蔽——`gpu_id` 只能填 0/1/3/4/5/6/7，**绝不能填 2**。
- **对 π0.5 路线的硬约束**：openpi 官方估算 π0.5 LoRA 微调需 >22.5 GB、全量 >70 GB。单张 3090（24 GB）跑 LoRA 处于**临界**（须 bf16 + gradient checkpointing 甚至 offload，需实测）；**全量微调单卡不可能**，多卡 FSDP/DeepSpeed（7 卡共 168 GB）理论可行但受共享占用与 3090 无 NVLink 的并行效率制约。这从算力侧**进一步支持 07-21 版的优先级**：先用轻量骨干/小诊断模型验证 H2（动作条件增益），π0.5 留作最终验证骨干；π0.5-LIBERO checkpoint 的推理/评测显存远小于训练，预计单卡可行（W1–2 实测确认）。
- 阶段 A 的诊断模型（小型动作编码器 + 结构化目标分类/检索头）单张 3090 绰绰有余。§6 问题 3 的 GPU 部分现已可回答：**7× RTX 3090 24GB，共享使用**。

### 5.2 RoboTwin 2.0 环境已就绪（本地事实）

- 部署于 `/bigbig_nfs_share/lijunhui/Robotwin2`（官方仓库 commit `c3ddfa8b`；SAPIEN 3.0.0b1 / CuRobo 0.7.8 / PyTorch 2.4.1+cu121 / Python 3.10 / 项目内 CUDA 12.1）；唯一激活入口 `Robotwin2/config/activate_robotwin2.sh`。
- 官方资产已下载校验解压；渲染验证 `script/test_render.py` 输出 `Render Well`；数据采集链路已用 `beat_block_hammer` 3-episode 冒烟打通（落在空闲物理 GPU 3）。域随机化（clean/randomized）、50 任务、多本体均可在 `task_config/` 配置——**`<视觉,动作,指令>` 数据可本地自产，不依赖官方预采数据**。

### 5.3 本地数据 schema 实测（回答 07-21 版 §5.6 的工程未知项）

对本地采集的 `demo_clean_smoke/episode0`（517 步）实测：

- `data/episodeN.hdf5`：`observation/{head,front,left,right}_camera/{rgb(JPEG bytes), intrinsic_cv, extrinsic_cv, cam2world_gl}` + `joint_action/{left_arm(6), right_arm(6), 左右 gripper, vector(14)}` + `endpose/{left,right}_endpose(7=xyz+四元数) + gripper`；本配置下 `pointcloud` 为空。
- `instructions/episodeN.json`：`{seen: [...], unseen: [...]}`，每集数十条多样自然语言指令——三元组中"指令"一项现成且带 seen/unseen 划分。
- **HDF5 中没有 `step_name`，也没有逐帧语义标签**（该 commit 源码中 `step_name` 仅出现在调试用 `save_camera_images`，不进采集管线）。⚠️ 早期分析（07-11/07-21 文档）把 `step_name` 当"免费原子切分锚点"的假设**在本地数据上不成立**，事件/原子边界须另行获取，可行途径按成本排序：
  1. `_traj_data/episodeN.pkl` 保存了每次运动规划调用的关节轨迹段（本集右臂 5 段）——**天然的粗粒度动作段边界**（但无语义名）；
  2. 从 gripper 通道/仿真真值提取夹爪开合、接触、物体状态变化事件；
  3. 在任务 `play_once` 技能 API 调用处插桩，采集时记录语义步名与帧号（语义最准、改动小，但属修改官方源码，须先与用户/师哥确认）。
- 仿真真值（物体位姿/谓词）采集时可从 SAPIEN 场景直接读取——累计 delta / Δobject / Δpredicate 标签可零成本构造（需插桩保存，同上）。

### 5.4 对实施路线的本地化修订

- 07-21 版第一阶段主战场是 LIBERO（BDDL 谓词干净），但 **LIBERO 与 openpi 本地均未安装**；按工作区约定须各建独立环境（与 RoboTwin 基础环境互不污染），这是阶段 A 前的一次性成本。
- 本地已就绪的是 RoboTwin：可先用它做**标签流水线原型**（事件切分 + 真值谓词 evaluator + 插桩产出 `<视觉,动作,事件段,指令>`），LIBERO 环境并行安装；正式 H2 诊断是否仍以 LIBERO-Goal 为主，列入与师哥确认事项。
- 决策闸门 G0–G3 与时间线不变；W1–2 交付物中"跑通 π0.5-LIBERO inference"在 3090 上先测推理显存，LoRA 可行性单独实测后再定阶段 B 的骨干改造深度。

---

## 6. 待与师哥确认的关键问题（07-21 版压缩）

1. 首要产出是 method paper 还是允许 diagnostic benchmark fallback？
2. 是否同意把核心收缩为 causal, ambiguity-aware **A2FI**？先做 H2/A2G 再改 π0.5？
3. GPU 资源（型号/显存/时长）——fvl09 现状见 §5.1（7× RTX 3090 24GB 共享）；π0.5 是否必须为第一骨干（LoRA >22.5GB，全量 >70GB）？
4. 控制主指标选 LIBERO-Goal OOD 还是 LIBERO-Long/PRO；H1 最小效应量如何预注册？
5. 是否接受 Anchor-Align 为最重要 baseline（"超过低层方向标签"为最低门槛）？
6. （新增，2026-07-26）标签流水线原型先在本地 RoboTwin 做还是等 LIBERO 装好；是否同意在任务代码技能 API 处插桩记录语义步名与真值。

---

## 7. 外延想法索引（仅索引，明确**非主干**）

源仓库中围绕主干发散出的想法，按用户要求不搬运正文，仅列条目备查：

- 因果不变性表征（同意图不同路径→表征接近；同 delta 不同物体状态→不合并）；
- "已完成什么/为什么做/置信度"三层输出；
- A2FI disagreement 作为失败预警/人机干预信号（可解释性应用）；
- predicate delta 序列替代单一 pose delta 的信息量消融；
- 把 Anchor-Align 从对手变起点的递进叙事（单 chunk L1 → 多 chunk L2/L3 + 歧义 + 反事实）。

> 以上详见源仓库 `前置论文/idea1-动作到功能性意图-重新评估与实施路线-2026-07-21.md` §11 及 `idea1-idea报告.md`。
