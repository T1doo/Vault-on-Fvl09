---
title: 未来动作条件意图理解——核心Idea与Mouse MVP状态
aliases:
  - 未来动作条件下的意图理解——Idea 内容分析
  - Future Action as Privileged Intent Supervision
  - 未来动作条件意图理解
  - Controlled Multi-Future Intent Identifiability and Semantic Compression
  - 未来动作条件意图理解_idea内容分析_2026.7.31
date: 2026-07-31
last_updated: 2026-08-26
status: current
design_version: v1
design_status: frozen
empirical_update_version: mouse_mvp_v1
empirical_as_of: 2026-08-20
empirical_status: mouse_mvp_data_complete_core_pass_temporal_unresolved
dataset_scope_accepted_roots: 4
dataset_scope_task_family: mouse_three_destination
dataset_scope_raw_trajectories: 24
dataset_scope_realizations_per_intent: 2
next_dataset_design_version: controlled_multi_future_f1_f4_v1_2
next_dataset_design_status: frozen_collection_not_started
next_dataset_formal_roots: 40
next_dataset_formal_raw_trajectories: 360
current_data_construction_protocol: "[[数据构造/数据构造方案]]"
formal_generalization_claim: false
h_reveal: null
compression_status: not_started
policy_transfer_status: not_started
tags:
  - idea1
  - VLA
  - future-action
  - intent
  - action-compression
  - RoboTwin
---

# 未来动作条件意图理解——核心Idea与Mouse MVP状态

> [!abstract] 一句话定义
> **训练时，以当前时刻的观测图像与机器人状态为锚点，把从该时刻开始的一段未来动作序列作为特权信息，让 VLA 推断轨迹所表达的可验证行为目标／操作程序；核心研究未来看多远 $H$、不同未来共享多久 $P$，以及覆盖相同未来后最少压成多少 token $K$。部署执行时仍使用正常策略接口，不向机器人额外提供真实未来动作。**

> [!summary] 当前实证状态
> 截至 2026-08-20，Mouse 三目标 controlled multi-future MVP 已完成 4 个 accepted roots、24 条 formal raw trajectories、144 个 derived views 与 24 条四视角 MP4。冻结小模型仅在 g7+g8 上训练并拟合 normalization；结果表明，在一次性裁决时未参与训练、normalization 和 checkpoint 选择的 g11+g12 两个独立 root 上，future／step-delta 内容支持目标识别、同意图跨路径一致性与 future replacement prediction-switch。但自然时间顺序尚未稳定优于 endpoint-only 与 temporal-shuffle。当前机器结论为 `core pass / temporal unresolved`，因此 $H_{\mathrm{reveal}}$ 仍为 `null`，$K$/compression 与 policy transfer 尚未开始。

> [!important] 当前最准确的项目结论
> **在严格受控的 same-current 多未来数据中，future／step-delta 内容已经表现出跨独立 root 的结构化目标诊断价值；但模型尚未表现出对动作时间顺序的必要依赖。正式 anchor-based $H/P$ reveal、长动作语义压缩 $K$、任务族泛化与部署策略迁移仍是后续问题。**

> [!danger] 不可再次颠倒的时间方向
> 正确样本是
> `当前图像 o_t + 当前机器人状态 s_t + 未来动作 a_t:a_{t+H-1} → 意图 y_t`
> 而不是
> `当前／最终图像 + t 之前已经发生的动作 → 已完成行为／意图`。

![[Idea/归档/2026-08-25_其余Idea材料/Pictures/image from Idea.png]]

## 阅读导航

| 想先回答什么 | 跳转 |
|---|---|
| 这个 idea 到底是什么？ | [[#1. 正确的问题定义]] |
| 目前实际完成到了哪里？ | [[#11. 当前实证状态（截至 2026-08-20）]] |
| “未来动作”在离线数据里到底指什么？ | [[#2. 最容易再次混淆的边界]] |
| 为什么不再以 left/right 为主？ | [[#4. 从二元左右升级为复杂多物体歧义]] |
| Mouse MVP 属于哪一层难度？ | [[#4.3 推荐的难度阶梯与当前落点]] |
| “多少 future token”怎样严谨研究？ | [[#5. 真正的核心：H、P、K、L 是不同变量]] |
| 为什么当前 $L=2$ 不是 $H_{\mathrm{reveal}}$？ | [[#5.4 当前诊断变量：分支点后 suffix 长度 $L$]] |
| 为什么同一意图也必须有多条轨迹？ | [[#3.3 同一意图、多种执行实现]] |
| 长动作可以怎样编码？ | [[#7. 长未来动作的编码路线]] |
| 怎样接入 π0.5 又不改变部署接口？ | [[#8. 训练与部署的信息流]] |
| 与 PRTS、LACY 等怎样划界？ | [[#10.1 2026-07-31 最近工作核查与新颖性边界]] |
| 当前哪些问题仍未解决？ | [[#12. 已解决与仍未解决]] |
| 下一阶段做什么？ | [[#13. 下一阶段正式数据方案：四类 Controlled Multi-Future 场景族]] |
| 当前固定数据怎样具体构造与验收？ | [[数据构造/数据构造方案]] |
| F1–F4 机制模型怎样训练、选 checkpoint 与统计？ | [[数据构造/数据构造方案#第二部分：F1–F4 机制模型训练与评测协议（Deferred）|机制模型训练与评测协议]] |
| 未来 π0.5 mixing 在哪里单独设计？ | [[数据构造/数据构造方案#第三部分：多任务训练混合与 π0.5 接入协议（Deferred）|π0.5 接入协议]] |
| GPT 三轮审阅历史在哪里？ | [[#附录：设计审阅历史]] |
| 历史数据规范怎样追溯？ | [[Idea/归档/2026-08-25_其余Idea材料/未来动作意图数据集构造方案_2026.7.31_简明版|2026-07-31 简明版（历史归档，不是当前执行规范）]] |
| 历史完整 Schema/Gate 怎样追溯？ | [[Idea/归档/2026-08-25_其余Idea材料/未来动作意图数据集构造方案_2026.7.31|2026-07-31 完整版（历史归档，不是当前执行规范）]] |

---

## 0. 文档职责与信息源优先级

本文同时承载两类彼此不能混淆的内容：

1. **冻结研究定义**：问题、时间方向、$H/P/K/R/L$、训练／部署边界、数据单位与可证伪 Gate；
2. **版本化实证更新**：Mouse MVP 已经实施了什么、机器证据支持什么、仍不能声称什么，以及下一停止点。

### 0.1 研究定义优先级

1. 用户／师哥后续明确纠正；
2. 2026-07-31 的 [[Idea/归档/2026-08-25_其余Idea材料/Idea|原始 Idea]] 与 [[Idea/归档/2026-08-25_其余Idea材料/Pictures/image from Idea.png|原始截图]]；
3. [[数据构造/数据构造方案|合并总方案]]中的数据、机制评测与 policy-transfer 三个职责部分；
4. 固定 revision 的官方论文、代码与数据，仅用于核实外部事实。

### 0.2 实证事实优先级

1. formal raw、receipt、verifier、acceptance audit、closure receipt 与 final seal；
2. final model result、evaluation report、checkpoint 与 GPU pre/post provenance；
3. [[数据构造/初步尝试 2026.8.25/简单尝试 2026.8.10 .md|append-only 实时日志]]中的更晚机器记录；
4. [[数据构造/初步尝试 2026.8.25/成果复盘|成果复盘]]与阶段快照；
5. 人工描述和便阅 MP4。

当冻结设计与后来服务器事实冲突时，保留原设计历史，同时以版本化 empirical update 记录修正；不能悄悄把后来才知道的结果倒写成 7 月 31 日就已验证的事实。

> [!warning] 历史材料边界
> 旧文档曾把输入动作解释成“已经发生／历史动作”，已整体移至 [[Idea/归档/2026-07-31_偏离口径_已执行动作路线/README|归档说明]]。
> `论文/前置论文/` 和该归档都不能反过来覆盖本文件中的时间方向与研究问题。

---

## 1. 正确的问题定义

### 1.1 以当前时刻为锚点

在一条机器人轨迹中选定当前锚点 $t$：

- 当前视觉观测：

$$
o_t=\{I_t^{head}, I_t^{wrist}, \ldots\}
$$

- 当前机器人状态：

$$
s_t=[q_t,\;g_t,\;\text{optional proprioception}]
$$

- 从当前时刻开始的未来动作片段：

$$
A^+_{t,H}=(a_t,a_{t+1},\ldots,a_{t+H-1})
$$

- 该未来分支所服务的轨迹可验证行为目标／操作程序：

$$
y_t
$$

动作压缩器把长序列变为 $K$ 个模型可读取的动作 token：

$$
Z^a_{t,H,K}=C_\phi(A^+_{t,H},\,\Delta t,\,m)\in\mathbb{R}^{K\times d_z}
$$

意图任务是：

$$
p_\theta\left(y_t\mid o_t,s_t,Z^a_{t,H,K}\right)
$$

这里的 $y_t$ 不表示无法从数据验证的心理动机，而是 `behavioral goal`、`trajectory-grounded subgoal` 或 `executable task-operation program`。重点不是把低层动作简单翻译成一句话，而是判断：

> **在当前场景存在多个合理未来时，给出多长的未来动作证据，模型才足以识别机器人究竟要完成哪个多物体操作目标？**

真实生成方向与模型推断方向不能写反：

$$
y_t\longrightarrow A^+_{t,H}
$$

$$
(o_t,s_t,A^+_{t,H})\longrightarrow \hat y_t
$$

前式表示行为目标和任务程序产生未来动作；后式才是本项目训练的逆推任务。未来动作是**关于意图的证据**，不是意图的物理原因。

### 1.2 与正常策略任务的关系

正常 VLA 策略仍然学习：

$$
(o_t,s_t,\ell)\rightarrow A^+_{t,C}
$$

其中 $\ell$ 是正常任务指令，$C$ 是策略一次预测的动作 horizon。

新增的训练期意图任务学习：

$$
(o_t,s_t,A^+_{t,H})\rightarrow y_t
$$

两者可以共享视觉—语言骨干、LoRA 或 Adapter，通过联合目标训练：

$$
\mathcal{L}
=
\mathcal{L}_{policy}
+
\lambda_{intent}\mathcal{L}_{intent}
$$

若希望主张“意图理解反哺动作预测”，则 $\mathcal{L}_{intent}$ 必须更新正常策略实际使用的共享参数；完全独立的分类器只能证明数据中存在可读的意图信息。

### 1.3 更准确的英文表述

推荐主表述：

> **Future Action as Privileged Intent Supervision**

或：

> **Future-Action-Conditioned Intent Inference**

其中：

- **future-action-conditioned**：未来动作是条件；
- **intent inference**：被预测的是隐藏意图；
- **privileged supervision**：未来动作主要在训练／诊断阶段可见，部署控制不依赖真实未来轨迹。

不建议单独写成 “future prediction”，因为本辅助任务并不是在预测未来动作；未来动作已经作为输入。

---

## 2. 最容易再次混淆的边界

### 2.1 离线轨迹已被记录，不等于它对样本是“过去”

一条演示轨迹在磁盘上当然已经采集完毕，但时间含义必须相对样本锚点 $t$ 定义：

```text
完整离线轨迹

... a_{t-2}, a_{t-1} | o_t, s_t | a_t, a_{t+1}, ... a_{t+H-1} ...
         过去部分       当前锚点              未来动作输入
```

因此，构造样本时从轨迹文件中读取 `t:` 之后的数据，也必须称为：

- future actions relative to anchor $t$；
- 未来专家动作；
- 未来轨迹片段；

不得因为它来自一条已保存的 demonstration，就改称“已经执行的历史动作”。

### 2.2 当前 Mouse MVP 中的未来动作来源

第一阶段仍以成功的专家／规划器轨迹为事实来源，从相对锚点 $t$ 的未来控制区间截取动作；但服务器动作语义已经不再是待确认状态。

Mouse MVP 冻结的 primary future stream 为：

```text
controller_effective_setpoint_v1
250 Hz

12 维双臂 effective position target
+ 12 维双臂 effective velocity target
+ 2 维 normalized gripper command
= 26 维 / action interval
```

同时保存但分流使用：

- planner position／velocity target 与 path audit；
- controller requested command；
- simulator drive-target readback；
- realized qpos／qvel／EEF state；
- timestamp、component update mask；
- object、contact、predicate 与 verifier 审计字段。

每条正式轨迹严格满足：

```text
N actions / N+1 states
state[k] -- action[k] on [k,k+1) --> state[k+1]
```

> [!important] 动作语义边界
> planner、requested command、effective setpoint、drive readback 与 realized state 是不同的数据流，不能混称为同一种 action。当前主模型使用 effective setpoint；其他流只作审计或预注册消融。Mouse MVP 没有把 future RGB 作为模型输入。

“使用策略自己预测的未来动作再判断意图”仍只是可研究的鲁棒性或闭环扩展；它会引入策略误差，不能替代第一阶段的干净专家 future 定义。

### 2.3 训练可见与部署可见

| 信息 | 正常策略训练／部署 | 训练期意图分支 |
|---|---:|---:|
| 当前图像 $o_t$ | 是 | 是 |
| 当前机器人状态 $s_t$ | 是 | 是 |
| 正常任务指令 $\ell$ | 是 | 默认屏蔽 |
| 真实未来动作 $A^+_{t,H}$ | 作为策略监督 target；部署未知 | 作为特权输入 |
| 未来图像／未来物体状态 | 否 | 默认禁止 |
| 意图标签 $y_t$ | 非部署输入 | 监督 target |

> [!important] 为什么意图分支默认屏蔽指令
> 若原始指令已经写明“把红杯放进蓝盒”，模型可以复述指令而不读取未来动作。
> 数据可以保留原始指令作为 raw metadata，但进入意图分支前必须显式 mask，并设置 instruction-only 对照。

### 2.4 本项目不是以下任务

- 不是 `past actions → what just happened` 的已完成行为识别；
- 不是只看末帧判断最终左右关系；
- 不是把动作方向直接分类成 left/right；
- 不是让部署策略凭空读取真实未来；
- 不是把整条轨迹平均成一个向量后直接宣称“理解长动作”；
- 不是只训练一个与策略完全隔离的 probe 后宣称控制得到改善。

---

## 3. 为什么未来动作是有价值的特权信号

仅给当前图像与机器人状态时，同一场景通常允许多种合理意图：

$$
p(y\mid o_t,s_t)
$$

可能是多峰的。加入未来动作后：

$$
p(y\mid o_t,s_t,A^+_{t,H})
$$

应当随着动作证据增多而逐渐收缩。

```mermaid
flowchart LR
    O["同一个当前观测 o_t<br/>同一个机器人状态 s_t"]
    O --> Y1["意图 1<br/>移动红杯到蓝盒"]
    O --> Y2["意图 2<br/>把红杯堆到绿块上"]
    O --> Y3["意图 3<br/>先移红杯，再关闭抽屉"]
    O --> Y4["意图 4<br/>交换两个物体的位置"]

    Y1 --> A1["未来轨迹 A⁺₁"]
    Y2 --> A2["未来轨迹 A⁺₂"]
    Y3 --> A3["未来轨迹 A⁺₃"]
    Y4 --> A4["未来轨迹 A⁺₄"]
```

如果当前图像已经唯一决定标签，未来动作没有必要；如果动作的第一个控制步就直接编码标签，任务也过于简单。好的数据应处在中间：

1. 当前观测本身有真实歧义；
2. 不同意图共享一段相似动作前缀；
3. 随着未来 horizon 增长，区别意图的证据逐步出现；
4. 只有结合“场景里有哪些物体”与“机器人未来怎样运动”，才能解释动作针对谁、要形成什么关系。

这也是该 idea 比二元 left/right 更有研究价值的地方。

### 3.1 Future replacement 测的是输入依赖，不是世界因果方向

保持 $o_t,s_t$ 不变，把 future A 替换为同组 future B，同时把正确 target 从 intent A 换为 intent B，是很强的受控输入干预：

$$
(x_i,A^+_{i,A,H})\rightarrow y_{i,A}
$$

$$
(x_i,A^+_{i,B,H})\rightarrow y_{i,B}
$$

它回答：

> 模型的输出是否对所提供的未来动作证据保持一致，并在证据变换后作出正确的 prediction switch？

推荐名称：

- **future-conditioned prediction-switch test**；
- **counterfactual input-dependence test**。

它不能单独证明“未来动作因果地产生意图”，因为真实生成方向是 intent／task program 先于轨迹。后文保留 “counterfactual group” 时，只表示“同一 current 下的替代可行未来”，不表示已经完成因果识别。

### 3.2 “意图”的可操作定义

一条把红杯放入蓝盒的轨迹，可能被自由语言解释为“整理桌面”“给绿块腾空间”或“清洁任务的第一步”。仅从当前状态与动作，无法判断哪一种更抽象的心理动机才是唯一真值。

因此本项目主监督限定为：

> **能由当前场景、未来动作及仿真 verifier 共同支持的行为目标、结构化子目标或可执行操作程序。**

主标签应满足：

- 对象、参照物、关系、顺序和约束可结构化；
- 成功条件可由仿真真值自动验证；
- 同义自然语言可从同一结构化程序派生；
- 不把无法从轨迹识别的更高层理由强行作为唯一答案。

论文标题和正文可以继续使用 intent，但首次出现时必须给出上述 operational definition，避免被理解成不可观测的 mental intent。

### 3.3 同一意图、多种执行实现

仅有 `one current → many intents` 仍可能退化成 branch ID／planner fingerprint 识别。更完整的数据单元应为：

$$
\mathcal G_i=
\left(
x_i,\;
\left\{
\left(
y_{i,j},
\left\{A^+_{i,j,r}\right\}_{r=1}^{R_{i,j}}
\right)
\right\}_{j=1}^{M_i}
\right)
$$

其中：

- $j$：同一 current 下的不同意图；
- $r$：同一意图的不同成功执行实现；
- $R_{i,j}$：该意图的 realization 数。

两个方向分别回答不同问题：

$$
\text{one current}\rightarrow\text{many intents}
$$

用于测量未来动作怎样消除当前观测歧义；

$$
\text{one intent}\rightarrow\text{many trajectories}
$$

用于测量模型是否对速度、路径形状、planner seed、暂停位置、可行接近方向与轻微 time warp 保持语义不变。

首轮 smoke 可以每个意图只生成 1–2 条 realization 来验证管线；进入主机制数据前，建议可行任务至少达到 $R\ge 3$，并保留 unseen-planner／unseen-path 测试。若成本不允许覆盖所有意图，应预注册覆盖比例，不能只给某一标签增加多样性。

> [!success] Mouse MVP 已落地的 realization 设计
> 当前每个 accepted root 已实际完成 `M=3, R=2`：三个 intent 各有一条 `r_pc` 和一条 `r_inv`。三个 `r_pc` 复用严格 canonical prefix，组成 `prefix_controlled` 主 cohort；每个 intent 的 `r_pc+r_inv` 组成独立 `trajectory_invariance` cohort。`r_inv` 不硬套 `r_pc` 的 $P$。这完成的是 pilot $R=2$，不取消正式机制数据在可行任务上达到 $R\ge3$ 的目标。

> [!warning] $R$ 不替代 $H/P/K$
> $R$ 是防止轨迹指纹的 nuisance-control/data dimension，不是新的论文主横轴。
> 为避免多实现把严格共享前缀 $P$ 压成 0，H/P 主 cohort 应复用同一 canonical prefix，再只在分叉后的后缀生成同意图多实现；额外的自由路径不变性 cohort 可单独评测。
>
> planner seed／path variant 必须作为 anchor 之后的显式 realization intervention；不能为了生成多实现重新采样当前场景。所有 realization 共享同一 current bytes 与物理 anchor，并记录 `base_snapshot_hash + realization_spec`。
>
> 正式 train/validation/test 以完整 root group（必要时进一步以 scene family）为最小划分单位。同一 current 下的全部 intent、realization、H/K/mask/replacement 与 cohort view 必须同 split。`r1/r2` 用于拟合、`r3` 用于测试的做法只能标为 **in-group trajectory-invariance diagnostic**，不能作为 unseen-trajectory／unseen-current 主泛化结论，也不能用于正式模型选择。
>
> planner OOD 也不能靠把同组 realization 拆到 train/test 制造。train groups 只含 seen planner；完全 held-out test groups 对同一 test current／intent 同时生成 seen-distribution 与 unseen-family realization，做 test-only 配对比较，从而把 planner shift 与 current/group holdout 尽量分开。

### 3.4 模型到底输出什么：双评测协议

“结构化意图”如果不定义输出接口，后续很容易出现“训练做组内四分类，论文却声称开放理解任意意图”的越界。因此第一阶段固定两个互不混表的任务。

#### A. 机制主任务：same-group candidate retrieval／ranking

输入当前图像、状态、future prefix，以及该 group 的 canonical structured-intent candidates；模型对候选排序。它最适合回答：

- correct future 是否提供增量信息；
- 每个 comparison cohort 内 $\mathrm{IntentScore}(H\mid P,c)$ 如何变化；
- replacement 后预测是否切换；
- 同意图不同 realization 是否得到一致排序。

但 `intent_00／01／02` 只是 group-local 索引，不能实现成“共享表示 → 固定 $M$ 分类头”。令 $\mathcal U_{i,c}$ 为 comparison cohort 的候选程序集合，$y_{i,c,m}$ 为第 $m$ 个 canonical structured program。必须使用同一套共享的 candidate-conditioned scorer：

$$
u_{i,c,b,H,m}
=
F_\theta
\left(
o_i,\;
s_i,\;
A^+_{i,b}[0:H],\;
E_y(y_{i,c,m});\;
\mathcal U_{i,c}
\right)
$$

$$
p_\theta
\left(
y_{i,c,m}
\mid
o_i,s_i,A^+_{i,b}[0:H],\mathcal U_{i,c}
\right)
=
\frac{\exp u_{i,c,b,H,m}}
{\sum_q\exp u_{i,c,b,H,q}}
$$

这里不强制某一种架构：cross-encoder、dual-encoder 或联合候选集编码都可以；但候选的**语义内容必须实际进入评分**，所有候选共享参数，输出对候选排列应当置换等变／鲁棒，不能只读取 local ID、固定位置或 group-specific head。

当 input-observable compatible set $\mathcal Y^{obs}_{i,c,b,H}$ 大于 1 时，默认使用 partial-label／set-marginal objective：

$$
\mathcal L_{\mathrm{set}}
=
-\log
\sum_{y\in\mathcal Y^{obs}_{i,c,b,H}}
p_\theta
\left(
y\mid o_i,s_i,A^+_{i,b}[0:H],\mathcal U_{i,c}
\right)
$$

并报告兼容候选概率质量与校准；只有集合收缩为单例后才统计 branch-specific accuracy／switch。只有确有预注册先验依据时才使用 soft distribution；“兼容集合内均匀”只能命名为人为训练目标，不能冒充真实后验。候选顺序必须随机化并做 permutation consistency test，输入中不得出现 branch ID、文件名或固定 candidate position。

特别地，当 $\mathcal Y^{obs}_{i,c,b,H}=\mathcal U_{i,c}$ 时，$\mathcal L_{\mathrm{set}}=0$，不会提供 branch-specific 梯度，也不会自动约束集合内部 entropy；这正好反映输入尚未排除任何候选。此类短 H 可以只作不确定性评测，或另加明确命名的 `balanced_candidate_objective`／训练集先验校准项，但不能把它包装成由当前输入识别出的真实意图分布。

#### B. 泛化副任务：global structured program decoding

不提供 group 候选，直接从全局 ontology 预测可变长有序程序：

```text
num_steps
steps[1:L].{op, object, relation, reference}
constraints
```

step index 本身表达顺序，避免用一个平铺 `order` slot 假装能表示 `seq(place(...), close(...))`。对象槽位不能只输出可能对应多个实例的类别字符串；主标签应使用当前视图中可解析的 canonical referring expression，并由隐藏的 verifier-only instance ID 做评测映射。若两个实例在当前可见证据下仍不可区分，应使用 set-valued reference 或把该样本排除出 instance-level exact match，不能强迫模型猜 simulator ID。segmentation mask／bbox 只作 grounding 评测与审计，默认不进入主模型。

该任务用于测对象 grounding、未见组合与多阶段操作程序泛化。其 program exact match、step-level slot accuracy、reference resolution、sequence edit distance 与 compositional OOD 指标必须独立报告。自由文本／自由 JSON 生成可作为后续扩展，但不作为首轮主任务或唯一真值。

### 3.5 Candidate universe 必须在 rollout 前冻结

同一 current 的 candidate universe 应在任务／物理可行性审计后、调用主 planner 生成分支之前冻结并记录 hash。必须区分：

- **task／physical feasibility**：目标在当前物理状态和约束下是否成立／可实现，记录判定器、证据、版本与不确定性；
- **planner solvability**：指定 planner／配置在给定次数内是否找到并执行成功的轨迹。

主 planner 成功不能反过来定义“物理可行”。若一个已冻结候选经审计可行、但当前 planner 连续失败，不得悄悄从候选集合删除；只能：

1. 按预注册上限重试或换用记录清楚的 planner；
2. 将 group 标记为 `incomplete`／`formal_cohort_eligible: false`；
3. 或整组不进入正式 balanced cohort，并报告 group-level attrition。

所有失败尝试、planner family／config、尝试次数和成功 realization 数都要保留。否则最终 candidate universe 会被 planner 成功率筛选，模型可能只学到“什么目标容易规划”，而不是 future action 中的意图证据。

---

## 4. 从二元左右升级为复杂多物体歧义

### 4.1 left/right 的正确位置

`left_of`／`right_of` 可以保留为：

- 数据管线 smoke test；
- snapshot 恢复与反事实分支验证；
- 最简单的 action-conditioning sanity check。

但它不能承担主结论，因为“向左运动”可能直接暴露 `left`，模型无需绑定物体、关系或长时程结构。

### 4.2 主场景应具有的结构

> [!important] 数据为 H/P/K 服务，不以复杂 benchmark 为先
> 多物体不是越多越好。第一阶段只需要少量、严格受控的任务族，使 visual-only 和方向／终点捷径失效，并能人为控制共享前缀 $P$。只有核心机制成立后，才扩展任务数量、组合复杂度与 OOD benchmark。

建议把每个场景表示成一个多物体关系图：

$$
G_t=(V_t,E_t)
$$

其中：

- $V_t$：可见物体、容器、抽屉、托盘、机械臂等实体；
- $E_t$：`left_of`、`inside`、`on_top_of`、`near`、`open` 等当前关系；
- 意图 $y_t$：要对图执行的结构化变换或有序操作程序。

首批主场景只需达到足以排除捷径的最低复杂度，例如：

- 多个可操作物体；
- 多个可作为参照／容器的物体；
- 外观相似或同类别 distractor；
- 至少一种会造成路径或选择歧义的障碍／空间约束；
- 同一初始状态下不少于三条可成功执行的未来分支。

数量不是越多越好。复杂度应按“是否迫使模型做对象—动作 grounding、是否形成延迟消歧”验收，而不是只数桌面上摆了几个道具。

### 4.3 推荐的难度阶梯与当前落点

| 层级 | 同一当前状态下的未来分支 | 意图证据何时出现 | 用途 |
|---|---|---|---|
| S0：方向 smoke | 同一物体放左／右 | 搬运方向很早出现 | 只验管线 |
| S1：对象选择 | 抓不同物体去同一容器 | 接近／抓取阶段出现 | 验对象 grounding |
| S2：目的地选择 | 抓同一物体，送往不同容器／参照物 | 抓取前缀相同，搬运后出现 | 主 horizon 入门 |
| S3：共享第一子任务 | 先完成完全相同的一步，再在第二步选择不同物体或关系 | 第一子任务结束后才出现 | 长 horizon 主体 |
| S4：顺序与组合 | 使用相同物体和近似终态，但操作顺序／约束不同 | 需跨多个事件整合 | **下一阶段 temporal-order 主任务** |

> [!summary] 当前数据属于 S2，而不是复杂多阶段程序
> Mouse MVP 的结构化程序是 `place(mouse, on_surface_of, destination)`：同一只 mouse 去 pad／scale／stand，属于目的地选择 S2。它有约 4.6 秒的共同 approach／grasp／lift 前缀，但尚未实现“先完成一个共同子任务，再操作第二个对象”的 S3，也没有证明相同终点下的顺序程序理解。S1/S2 继续承担 grounding 与 replacement sanity check；S4 现在提升为下一阶段的必要数据类型，而不再只是可选扩展。

### 4.4 一个真正有区分力的反事实组

> [!note] 概念示例，不是当前采集规范
> 本节只说明多物体、多阶段、晚期分叉为什么有区分力，当前 24 条 Mouse MVP 轨迹尚未覆盖。下一批数据的唯一冻结场景、规模与采集 Gate 以 [[#13. 下一阶段正式数据方案：四类 Controlled Multi-Future 场景族]] 的 F1–F4 为准，不能从本例另行扩展候选任务。

同一场景中可见：

- 红杯、蓝杯；
- 绿块、黄块；
- 蓝盒、灰盒；
- 一个抽屉、一个托盘；
- 若干相似 distractor。

从完全相同的当前快照分支：

```text
分支 A：
先把红杯放进蓝盒，
再把绿块放到托盘右侧。

分支 B：
先把红杯放进蓝盒，
再把黄块堆到绿块上。

分支 C：
先把红杯放进蓝盒，
再交换蓝杯与灰盒旁物体的位置。

分支 D：
先把红杯放进蓝盒，
再关上抽屉。
```

这些分支共享较长的第一个子任务。短 horizon 只能看到共同前缀，理论上不应高置信度猜出完整意图；只有覆盖第二阶段的未来动作后，意图才真正可识别。

> [!tip] “难”不是让轨迹更长
> 如果四条轨迹在第一步就朝四个方向走，再长也只是把早期答案重复很多次。
> 真正有用的难度来自：**共享前缀、多个候选对象、晚期分叉、组合关系与顺序信息。**

---

## 5. 真正的核心：H、P、K、L 是不同变量

用户和师哥提出的“输入多少未来 token”至少包含三个必须分开的变量。

### 5.1 变量一：未来覆盖长度 $H$

$H$ 表示从当前锚点开始纳入多少个原始动作时刻：

$$
A^+_{t,H}=(a_t,\ldots,a_{t+H-1})
$$

它回答：

> 模型需要看多远的未来，动作才开始充分暴露意图？

但 $H$ 必须同时报告：

- 原始 action step 数；
- 真实秒数；
- 数据采样频率；
- 覆盖了哪些语义事件。

只写 `H=50` 没有完整含义，因为不同数据频率下对应的物理时长不同。

### 5.2 变量二：共享未来前缀长度 $P$

$P$ 表示同一个 current 下、**指定 H/P comparison cohort** 中，多条未来动作从锚点开始保持完全相同的前缀长度：

$$
a^{(1)}_{t:t+P-1}
=
a^{(2)}_{t:t+P-1}
=\cdots=
a^{(M)}_{t:t+P-1}
$$

它回答：

> 数据把意图证据人为推迟了多久，模型在看到多少未来以后才有可能区分这些分支？

$P$ 应同时记录：

- raw action steps；
- 真实秒数；
- 共享事件数／子任务数；
- comparison-cohort-level 公共 $P$；
- 必要时的 branch-pair divergence step。

当 $H\le P$ 时，分支级完整意图尚不可识别；此时合理输出是兼容意图集合或分布，而不是高置信度 one-hot。

> [!important] $P$ 不属于无条件的 root group
> 同一个 root group 可以同时拥有一个或多个 `prefix_controlled` H/P cohort，以及不把 $P$ 作为受控主变量、也不进入严格 H/P 主曲线的 `trajectory_invariance` cohort。所有受控 P、prefix hash 和成员列表都必须挂在 comparison cohort 上，不能只在 group 根节点保存一个对所有 realization 都未必成立的 P。

> [!warning] 不同 $P$ 的 cohort 不天然可直接比较
> 每个 cohort 首先单独报告 $\mathrm{IntentScore}(H\mid P,c)$，再按 $P$ 分层做描述性汇总；不能因为长 $P$ cohort 更难，就直接宣称“增长 $P$ 因果地推迟 reveal”。只有共享同一 `matched_p_family_id`，且 candidate 数量／难度、程序结构、分叉后任务、planner、动作空间和总时长已匹配、原则上只改变共同前缀长度时，才做 $P$ 的直接对照。此时仍同时报告 $H-P$ 与 fixed balanced-candidate protocol 下相对同 cohort $H=0$ 的 $\mathrm{NLL}_{bal}$ reduction。

共享前缀还必须标注其语义类型：

| `prefix_type` | 含义 | 报告要求 |
|---|---|---|
| `kinematic_shared_path` | 共享低层运动／路径，但未完整覆盖共同子任务 | 重点报告 steps／seconds |
| `shared_semantic_subtask` | 共享一个或多个完整、可验证的子任务；其内部自然包含完成子任务所需的低层动作 | 同时报完整 event／subtask 数 |
| `mixed` | 完整共同子任务之外，还额外包含不构成新子任务的路径延长／中性停顿 | 分解报告两部分；默认不进入直接 matched-$P$ 效应比较 |

不能用人工等待、padding 或无任务意义的停顿来“做大 $P$”并混入主结论；这些时段必须单独标记并从 matched-$P$ 主比较中排除。推荐 cohort 字段为 `prefix_type`、`matched_p_family_id`、`candidate_difficulty_signature`、`post_divergence_program_family` 与 `contains_artificial_idle_or_padding`。

### 5.3 变量三：输入模型的 token 数 $K$

$K$ 是压缩后送进意图分支的动作 token 数：

$$
C_\phi:\mathbb{R}^{H\times d_a}\rightarrow\mathbb{R}^{K\times d_z}
$$

它回答：

> 在已经覆盖同样长的未来时间后，最少用多少个模型 token 才能保留足够意图信息？

### 5.4 当前诊断变量：分支点后 suffix 长度 $L$

最终成功的 core diagnostic 没有直接从 root anchor 扫描 $H$，而是从审计已知的 branchpoint $B_b$ 后截取 suffix：

$$
A^{suffix}_{b,L}
=
\left(
a^{(b)}_{B_b},
a^{(b)}_{B_b+1},
\ldots,
a^{(b)}_{B_b+L-1}
\right)
$$

- $L$：从已知 branchpoint 后截取的诊断 suffix steps；
- $H$：从真实模型 current anchor 开始覆盖的完整 future-action steps；
- 对 `r_pc`，严格 branchpoint 与该 cohort 的 $P$ 对齐；
- 对 `r_inv`，只按各自真实语义事件起点做 trajectory-invariance 诊断，不把 $P$ 强加给它。

当前冻结网格是：

```text
L = [1, 2, 4, 8, 16, 32, 64, 128, 256]
```

网格中的 $L\in\{2,4,8,16,32,64,128,256\}$ 均为 core pass，$L=1$ 未完整通过；但 endpoint-only 与 temporal-shuffle 未稳定下降。机器 artifact 与本文语义解释必须同时保留：

```text
formal artifact field:
first_core_passing_horizon_steps = 2

本文的语义解释:
first_core_passing_suffix_L = 2

formal anchor-based result:
h_reveal = null
```

机器 artifact 沿用历史字段名 `first_core_passing_horizon_steps=2`；本文为避免与 anchor-based $H$ 混淆，将它解释为 `first_core_passing_suffix_L=2`，不表示 artifact schema 已被改写。不能写成 `H_reveal=2`、`H=2` 或“意图在 8 ms 后出现”。只有从真实 root anchor 输入完整 canonical prefix + suffix，并在顺序敏感任务上通过 temporal 与正式 $H/P$ Gate 后，才可能讨论 anchor-based $H_{\mathrm{reveal}}$。

### 5.5 K 之外还要报告表示占用；有可复核码长后才报告编码率

相同 $K$ 不一定表示相同容量。例如，16 个连续 1024 维 float token 与 16 个词表大小为 1024 的离散 token，不是公平的等预算比较。

对未量化连续 token，应报告 representation footprint／interface storage cost：

$$
F_{\mathrm{repr}}^{cont}=K\,d_z\,b_{\mathrm{store}}
$$

离散 token ID 在相同接口边界的 footprint 为：

$$
F_{\mathrm{repr}}^{disc}
=
N_{\mathrm{tok}}\,b_{\mathrm{id,store}}
$$

其中 $d_z$ 是 token 维度，$b_{\mathrm{store}}$ 是每维实际存储位数，并按覆盖时长报告：

$$
R_{\mathrm{repr}}=\frac{F_{\mathrm{repr}}}{\tau_H}
$$

这些量固定测量 `compressor serialized output → VLA input adapter` 的接口表示占用，不能称为 channel capacity、有效信息量或互信息。离散 ID 查表后的 $d_{\mathrm{model}}$ embedding activation、KV cache 与运行显存另作 compute／activation cost，不能混入 footprint。

对离散／量化 token，若明确 codebook、量化精度和实际编码规则，可报告固定长码或估计码长：

$$
B_{\mathrm{code,nom}}^{disc}
=
K\left\lceil\log_2|\mathcal V|\right\rceil,
\qquad
R_{\mathrm{code,nom}}
=
\frac{B_{\mathrm{code,nom}}}{\tau_H}
$$

若实际执行 bit packing／熵编码，或使用 held-out token 概率估计码长，则另报告：

$$
B_{\mathrm{encoded}},
\qquad
R_{\mathrm{encoded}}
=
\frac{B_{\mathrm{encoded}}}{\tau_H}
$$

必须谨慎解释：

- 未量化 float token 的有效语义容量不能仅靠位数精确刻画；
- 可变长 tokenizer 应报告 token 长度分布，而不是只报平均值；
- compressor 参数量、FLOPs、显存、延迟和训练数据也要同时匹配／报告。
- 离散固定长码的 bit 数同样不等于模型真正使用的互信息。

因此主结果分两层：

```text
Intent score vs K
Intent score vs representation footprint

仅在具有可复核 bitstream／held-out 估计码长的编码实验中：
Intent score vs encoded rate
semantic distortion vs encoded rate
action reconstruction vs encoded rate（仅作辅助）
```

其中 semantic distortion 可以预注册为 $1-\mathrm{IntentScore}$ 或结构化风险；重构误差低不代表意图保真高。

> [!warning] matched-rate 的使用边界
> 未量化连续 K-query 与 FAST 等离散 tokenizer 之间默认只能做 **matched representation-footprint comparison**，同时匹配／报告 K、$d_z$、dtype、参数量和计算量。只有双方都有明确量化／编码账本，能给出可复核 bitstream 或估计码长时，才使用 **matched-rate comparison**。即使 matched-rate，也不能写成“等互信息”。

### 5.6 绝对不能混为一谈的量

| 符号 | 含义 | 是否等于“future token 数” |
|---|---|---|
| $T$ | 整条原始轨迹长度 | 否 |
| $H$ | 当前样本覆盖的未来原始动作步数 | 是“看多远”，但还不是压缩 token 数 |
| $\tau_H$ | $H$ 对应的真实物理时长 | 否，但必须报告 |
| $P$ | 多条未来完全相同的共享前缀长度 | 否；它控制“证据多晚出现” |
| $L$ | 从审计已知 branchpoint 后截取的 suffix 长度 | 否；当前 core 诊断使用它，不能冒充 $H$ |
| $C$ | 正常策略一次预测的 action horizon | 否，除非实验特意令其相等 |
| $N_{raw}$ | 某种 tokenizer 对原始动作产生的 token 数 | 不一定 |
| $K$ | 本项目 compressor 输出给 VLA 的动作摘要 token 数 | 是“压成几个” |
| $F_{\mathrm{repr}}$／$R_{\mathrm{repr}}$ | 表示占用／每秒表示占用 | 不是信息量；用于记录未量化接口成本 |
| $B_{\mathrm{code,nom}}$／$R_{\mathrm{code,nom}}$ | 离散／量化表示的固定长 nominal code budget | 不是实际码率或互信息 |
| $B_{\mathrm{encoded}}$／$R_{\mathrm{encoded}}$ | 可复核实际 bitstream／held-out 估计码长 | 可用于 matched-rate；仍不等于互信息 |

> [!danger] 错误实验
> 只比较 `K=8/16/32`，但每个 K 同时覆盖不同 H 或使用不同 P，会无法判断收益来自“看得更远”“更早分叉”还是“编码得更细”。

### 5.7 正确的分阶段实验

第一阶段固定为 raw／近似无压缩动作，交叉控制 $H$ 与 $P$，先回答未来动作是否提供信息、意图何时 reveal：

$$
\text{IntentScore}_{raw}=f(H\mid P,c)
$$

只有机制通过后，第二阶段才在每个固定 comparison cohort $c$ 及其 $H,P$ 下交叉比较压缩预算 $K$：

| $H \backslash K$ | 4 | 8 | 16 | 32 | raw／近似无压缩 |
|---:|---:|---:|---:|---:|---:|
| 短未来 | ✓ | ✓ | ✓ | 可选 | ✓ |
| 中未来 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 长未来 | ✓ | ✓ | ✓ | ✓ | 资源允许时 |
| 完整语义段 | ✓ | ✓ | ✓ | ✓ | 资源允许时 |

得到的不是一条孤立曲线，而是：

$$
\text{IntentScore}=f(H,K\mid P,c,\text{compressor})
$$

由此可以回答：

- 给定 comparison cohort 与共享前缀时的最小充分未来 horizon $H^\*(P,c)$；
- 在 matched-$P$ family 内，共享前缀 $P$ 的受控改变如何推迟 intent reveal；未匹配 cohort 只作分层描述；
- 给定 $H,P,c$ 时的最小充分 token 数 $K^\*(H,P,c)$；
- 给定 $H,P,c$ 时达到同等语义性能的最小 representation footprint；
- 可复核编码时达到同等语义性能的最小 encoded rate；
- 哪种压缩器在相同 $H,P,c,K$ 下保留更多意图；
- horizon 增长后，固定 K 是否成为信息瓶颈；
- 过长未来是否引入无关动作并导致性能下降。

---

## 6. “意图何时出现”：前缀遮挡与证据涌现

### 6.1 Prefix reveal

固定同一条完整未来轨迹，只逐步开放前缀：

```text
H = 0       只给当前图像和状态
0 < H ≤ P   仍处于完全共享前缀，完整分支意图不可辨认
H > P       开始看到真实分叉证据
H = h3      看到目的地选择
H = h4      看到第二个子任务
H = full    覆盖完整语义段
```

画出：

$$
\mathrm{Acc}(H\mid P),\quad
\mathrm{NLL}(H\mid P),\quad
\mathrm{Entropy}(H\mid P)
$$

理想现象不是从第一步就满分，而是：

```text
不可辨认 ── 共同动作前缀 ── 关键分叉事件 ── 置信度上升 ── 饱和
```

> [!important] $H\le P$ 是不可辨认的充分条件，不是 compatible set 的唯一触发条件
> 即使 $H>P$，planner 数值可能已经分叉，但对象选择、目的地或结构化程序在语义上仍未区分。
> 对 `prefix_controlled` 主 cohort，compatible set 不应由“目前碰巧采到的轨迹”决定。令 $\mathcal T_{i,c}$ 是 comparison cohort $c$ 的版本化任务树。必须同时保存两个边界：
>
> - $n^{oracle}_{i,c,b}(H)$：可使用 future object pose、contact、success predicate、planner／verifier phase 的 oracle 节点，只作审计和解释；
> - $n^{obs}_{i,c,b}(H)$：只能由当前图像、白名单当前状态、future-action prefix、timestamp／mask 的预注册确定性规则推进的 input-observable 节点，用于训练和主评测。
>
> 主 compatible set 定义为：
>
> $$
> n^{obs}_{i,c,b}(H)
> =
> g^{obs}_{\mathcal T_{i,c},v}
> \left(
> o_i,\;
> s_i,\;
> A^+_{i,b}[0:H],\;
> \mathrm{timestamp},\;
> \mathrm{mask}
> \right)
> $$
>
> $$
> \mathcal Y^{obs}_{i,c,b,H}
> =
> \operatorname{Leaves}
> \left(
> \operatorname{Subtree}_{\mathcal T_{i,c}}
> \left(n^{obs}_{i,c,b}(H)\right)
> \right)
> $$
>
> 记号中 $v$ 是 observable-evidence rule version。`Subtree` 包含节点自身，因此当 $n^{obs}_{i,c,b}(H)$ 已是 leaf 时，集合就是该 leaf，而不是空集。节点只能因模型输入中可获得的预注册结构证据而前进，不能因为第一次数值 jerk，或 hidden future object pose／contact／planner target／verifier phase 而收缩集合；也不能用测试模型准确率事后反推节点。若证据是否可观察存在争议，$n^{obs}$ 必须停留在更早的父节点，宁可让集合偏宽。
>
> oracle 节点同样可生成 $\mathcal Y^{oracle}_{i,c,b,H}$，但只能解释“环境真值何时发生了结构变化”，不得替代 $\mathcal Y^{obs}$ 训练标签。每个 derived view 至少保存 `tree_node_observable_at_H`、`tree_node_oracle_at_H`、两套 compatible IDs、`compatible_set_for_training: observable`、evidence-source 白名单和规则版本。同一 cohort 在 $H>P$ 后，不同 branch 可以拥有不同节点与 compatible set。observable 集合相对于预先枚举并冻结的 candidate universe／task tree 是结构化真值，不冒充“世界中所有物理可行意图”的全集；增加同义 realization 不应改变它。
>
> `trajectory_invariance` cohort 通常直接测同意图一致性；只有确需近似自由路径前缀兼容性时，才另定义：
>
> $$
> \widehat{\mathcal Y}^{emp}_{i,c,b,H}
> =
> \left\{
> y:
> \exists A'\in\widehat{\mathcal A}(x,y),
> \ d_H
> \left(
> A'[0:H],A^+_{i,b}[0:H]
> \right)
> \le\epsilon_H
> \right\}
> $$
>
> 并明确命名为 **empirical trajectory-compatibility set**，保存 realization-library hash、$d_H$、$\epsilon_H$ 和版本。它是有限轨迹近似，不替代任务树主标签，也不要求与 observable／oracle tree set 相等。差异应先报告采样覆盖与距离／阈值敏感性；只有当 empirical set 持续在 observable 结构证据前分离同一 compatible intents，并伴随 planner-ID probe 成功时，才把它作为轨迹指纹警报。
> $P$ 表示严格公共 raw prefix，`action_divergence_step` 表示数值分叉，`structural_reveal_event_observable` 与 `structural_reveal_event_oracle` 表示两种证据边界，$H_{\mathrm{reveal}}$ 表示按预注册指标得到的经验可识别边界；这些量不能互换。
>
> `H_reveal` 的定义必须在测试前预注册，但其数值依赖模型、checkpoint、指标和阈值，属于 evaluation artifact，不应写成 raw branch 的固定真值。

### 6.2 当前实证：future content 已通过，temporal order 未解决

截至 Mouse MVP，已观察到：

```text
future / step-delta 内容
→ 支持四个 root 上的目标识别
→ 支持同意图 r_pc / r_inv 一致性
→ 支持 future replacement prediction-switch
→ 通过 candidate permutation 与 mask Gate
```

但同时：

```text
temporal shuffle ≈ natural future（许多设置）
endpoint-only 经常也能达到高分
temporal contrast passing L = []
```

因此当前证明的是：**未来动作内容中存在可利用的目标诊断信息。**

当前尚未证明的是：**模型必须按正确时间顺序整合动作，才能理解长动作或结构化操作程序。**

> [!warning] 结论边界
> `core pass` 与 `temporal-order pass` 是两个独立 Gate。当前前者通过、后者未通过；不得用 replacement 正结果替代时间顺序证据。

### 6.3 除了前缀长度，还要做什么 mask

- **后缀 mask**：只保留前 $H$ 步，测自然证据涌现；
- **事件删除**：删除抓取、释放、第二子任务等完整事件；
- **局部时间遮挡**：删除一小段，定位关键时间区间；
- **合法时序重排**：保留完整事件块并重排；若对应另一个 candidate，target 同步切换并测 prediction-switch；
- **非法／OOD 时间打乱**：重排后不属于 candidate universe，不沿用原 one-hot，只测 reject／entropy／margin／OOD；
- **future replacement**：在同一当前快照下换成另一个真实未来分支，并同步切换监督 target；
- **endpoint-only**：只给起点／终点动作状态，检查是否根本不需要序列。

> [!important] Future replacement 的正确判定
> 保持 $o_t,s_t$ 完全不变，把 future A 替换成同 group 的真实 future B，监督 target 也必须从 intent A 切换为 intent B。
> 若模型仍坚持 A，说明它没有真正服从 future action。它比随机 shuffle 更强，因为 replacement future 仍然真实、可行且与当前 snapshot 匹配。
> 但只应在预注册的可辨认 horizon 上统计 branch-specific switch；当 compatible-intent set 仍含多个候选时，不能强求单标签切换。该实验是 counterfactual input-dependence test，不是“未来动作产生意图”的因果证明。

### 6.4 防止“第一次数值差异”变成 branch ID

严格共享 prefix 结束后，第一步很小的浮点差异可能来自 planner seed、jerk、padding 或时长，而不是语义事件。如果模型在 $H=P+1$ 立刻接近满分，首先应怀疑轨迹指纹。

首轮必须加入：

- 同一意图多轨迹实现 $R$；
- matched-duration sampling 与统一 padding；
- time-warp、速度归一化和轻微 path perturbation；
- 低通滤波后的动作对照；
- 删除分叉后的最初若干数值步；
- planner-ID／trajectory-length adversarial probe；
- unseen-planner 与 same-intent cross-trajectory 测试；
- 按结构化事件而非第一次数值分叉报告 reveal。

合理曲线应允许“数值已经分叉但完整语义仍未 reveal”的区间。若准确率只跟 `action_divergence_step` 而不跟对象／目的地事件走，当前任务仍更像 trajectory fingerprint classification。

### 6.5 层级意图可以怎样使用

复杂任务确实可以标注：

- 当前动作原语；
- 当前／下一子目标；
- 完整组合任务目标。

但第一版不必建立庞大的意图本体，也不能预先规定“短 H 就应该预测 primitive、长 H 就应该预测 task goal”，再把这种人工映射当成发现。更稳妥的做法是：

1. 以可验证的结构化 subgoal／task operation 作为主标签；
2. primitive 只作为动作阶段诊断，避免主任务退化成低层 action recognition；
3. 从同一结构化程序派生 primitive、subgoal、task 三种读取层级；
4. 在相同 $H,P$ 下分别画各层级的 reveal curve，让数据说明哪个层级何时可识别；
5. 不把语言模型自由生成的解释当作唯一真值。

这样既能分析“局部动作语义如何逐步上升到完整任务目标”，又不让标签体系盖过 `H/P/K` 主线。

---

## 7. 长未来动作的编码路线

### 7.0 动作表示层不等于压缩层

正式比较 $K$ 之前，必须先固定“同一 raw action 用什么坐标表示”。当前已经实际比较：

```text
raw absolute action
branchpoint residual
step delta
residual + step delta
```

实验发现：

- absolute action 存在明显的 cross-root offset；
- step-delta 更容易表达分叉方向和跨 root 的同意图差异；
- current visual embedding 是解释“动作方向对应哪个目标”的必要条件；
- visual proposal 存在 root-specific shift，patch visual embedding 相对稳定；
- 表示变化带来的收益不能被误称为 compressor 或 $K$ bottleneck 的收益。

下一阶段还应比较速度、加速度、方向变化与 event-relative action。只有 temporal representation 与 anchor-based $H/P$ Gate 通过，才进入固定 $H/P$/cohort 下的 $K$-token compression。

### 7.1 为什么不能只做简单平均

机器人动作具有稀疏而关键的事件：

```text
approach → align → grasp → lift → transport → place → release
```

均匀平均可能把短暂的夹爪切换、接触和方向改变冲淡；只取终点又会丢掉顺序与操作对象转换。

### 7.2 必须保留的简单基线

简单基线仍然重要，因为它告诉我们复杂模型是否真的必要：

1. raw sequence／padding；
2. 固定步长下采样；
3. 均匀 $K$ 窗口的 mean、std、首尾值、delta、速度峰值；
4. endpoint-only；
5. 累计 delta。

这些是可解释下限，不应被写成最终主方法，也不能因为“工程简单”而跳过。

### 7.3 DCT／FAST-style 频域基线

长动作压缩阶段应加入强于简单 stride 的频域基线：

1. DCT 系数按频率／幅值保留；
2. DCT + 量化；
3. FAST-style：DCT、量化、低频优先展平与 BPE。

[FAST](https://arxiv.org/abs/2501.09747) 的目标原本是高频机器人动作的离散 tokenization，而不是本项目的 intent bottleneck；它仍是非常相关的正式 baseline，因为它直接给出压缩—重构权衡。

需要注意：

- FAST 产生的是可变长离散 token 序列，不自动等于固定 $K$；
- 与未量化 $K$-query 比较时应固定 comparison cohort $c$ 及其 $H,P$，并按 token 长度分布、representation footprint、参数量与计算量匹配；
- 只有双方具有可复核实际／估计码长时，才补充 matched encoded-rate；
- DCT／FAST tokenizer 只能在 train split 拟合量化与 BPE；
- action reconstruction 是辅助指标，主指标仍是意图语义保真。

### 7.4 Temporal encoder + K queries

候选学习式压缩：

```mermaid
flowchart LR
    A["未来动作序列<br/>H × d_a"]
    N["动作语义归一化<br/>Δt / arm / gripper / mask"]
    E["Temporal Transformer<br/>或轻量时序编码器"]
    Q["K 个 learnable queries"]
    Z["K 个 action tokens"]
    V["当前视觉 + 当前状态"]
    P["Intent predictor"]

    A --> N --> E --> Q --> Z --> P
    V --> P
```

它允许固定 $K$ 读取可变长 $H$，适合直接研究 token bottleneck。

### 7.5 Event-aware compression

利用机器人事件边界切分：

- 夹爪开合变化；
- 末端速度谷值／停顿；
- 运动方向显著改变；
- 接近／离开物体；
- 接触建立与解除；
- 执行臂切换；
- 子任务验证谓词变化。

每个事件可以编码：

- 起止时间；
- 作用机械臂；
- 起止关节／末端状态；
- 路径统计；
- 夹爪状态；
- 与当前视觉对象的 grounding query；
- 事件在完整未来中的相对位置。

### 7.6 推荐主方法方向：多尺度事件—学习混合

纯手工事件会受阈值影响，纯 K-query 可能浪费容量学习明显的机器人边界。更值得验证的是：

```text
低层未来动作
   ├─ 局部细粒度编码：保留抓取、释放等短事件
   ├─ 事件边界候选：提供机器人先验
   └─ K-query 全局读取：跨事件整合长时程意图
```

但是否采用它应由同一 $H,K$ 下的实验决定，而不是先验认定更复杂一定更好。

### 7.7 动作 token 的最低元数据

无论使用哪种编码，都至少要显式保存／输入：

- `timestamp` 或 `sim_step`；
- action mask 与真实长度；
- 动作空间名称、维度、单位与归一化统计；
- 左／右臂和夹爪维度顺序；
- command action 与 realized state 的区分；
- 数据采样频率与任何重采样规则。

### 7.8 压缩比较的公平性清单

固定 comparison cohort $c$ 及其 $H,P$ 后，每个 compressor 至少报告：

| 维度 | 必须记录 |
|---|---|
| 接口长度 | $K$ 或可变 token 长度分布 |
| token 形式 | 连续／离散、$d_z$、dtype、量化 |
| 表示占用 | $F_{\mathrm{repr}}$、$R_{\mathrm{repr}}$，未量化连续接口只使用这一口径 |
| 离散／量化编码 | 词表／codebook、量化规则、nominal code budget $B_{\mathrm{code,nom}}$；可用时报告 $B_{\mathrm{encoded}},R_{\mathrm{encoded}}$ |
| 模型成本 | encoder 参数量、FLOPs、显存、延迟 |
| 训练成本 | 训练步数、数据量、随机种子 |
| 语义保真 | compatible-set、结构化 intent、replacement switch |
| 信号保真 | action reconstruction、事件保留，仅作辅助 |

不能把“相同 K”“相同 representation footprint”或“相同 encoded rate”直接写成“相同互信息”。未量化连续表示与离散 tokenizer 之间默认不使用 matched-rate 表述。

---

## 8. 训练与部署的信息流

### 8.1 任务匹配的 Gate：content → identifiability → H/P → K → policy

第一项机制结论必须使用 raw／近似无压缩未来动作，不让 learned compressor 成为混杂因素。最小输入仍包括 current-only、correct future、same-group replacement、no-vision、future-only 与 endpoint-only；但 temporal control 必须按语义作用分类，而不能全部理解为“性能越低越好”。

| 控制类型 | 例子 | 正确预期 |
|---|---|---|
| 合法时序重排 | event blocks 重排后对应另一个冻结 candidate | target 同步切换；测 temporal-reorder prediction-switch |
| 非法／OOD 顺序破坏 | reverse／shuffle 后不属于 candidate universe | 不使用原 one-hot；测 reject、entropy、margin 或 OOD score |
| 顺序保持的 nuisance 变化 | time-warp、速度缩放、保持事件顺序的重采样 | 结构化意图应尽量保持不变 |
| 信息删除 | endpoint-only、event-drop、局部时间遮挡 | 删除关键过程证据后，相关任务性能应下降 |

根据 Mouse MVP 的真实结果，研究 Gate 细化为：

1. **Future-content / prediction-switch Gate**：correct future 是否相对 current-only 提供目标信息，replacement 是否使预测切换；
2. **Cross-realization invariance Gate**：同 intent 的另一条真实路径以及 order-preserving nuisance 变化是否保持同一结构化目标；
3. **Task-conditioned Temporal Identifiability Gate**：先确认任务标签是否原则上依赖顺序。Mouse S2 可以是 order-insensitive；对 S3/S4，hard Gate 要求合法 program-order 变化切换到重排后的 target。非法／OOD 重排只作独立 calibration/rejection diagnostic；未预注册 reject head 时不决定 temporal pass；
4. **Formal anchor-based H/P Gate**：从真实 root anchor 扫 $H$，分别测 content-based reveal 与 order-sensitive reveal；不能以 branchpoint-aligned $L$ 代替；
5. **Compression Gate**：固定 cohort 与 $H/P$ 后比较 $K$、representation footprint 与 compressor。若要声称压缩保留长动作／程序顺序语义，必须先在 order-sensitive 任务上通过 Temporal Identifiability；
6. **Policy Gate**：前述目标层级与压缩机制通过后，才接入 π0.5、teacher–student 或 deployment-path alignment，并用真实 rollout 验证。

> [!important] S2 的正确解释
> 对“future 能否区分 pad／scale／stand”这个 S2 目标，时间顺序不一定是必要条件。shuffle 不下降既可能是模型没学顺序，也可能是标签只需要净位移、动作集合或 endpoint。现有 Mouse 数据负责定位这两种解释；真正的时间顺序主结论必须由 endpoint 难以区分的 S3/S4 数据承担。

若前置 Gate 不通过，应根据任务类型修正数据、动作表示、时间对齐、标签、模型或控制项；不能通过强迫 order-insensitive S2 变成顺序任务，也不能直接跳到大规模 compressor 或 π0.5 训练。

### 8.2 候选的后续联合训练框架（尚未冻结）

> [!warning] 候选信息流，不是 π0.5 执行规范
> 本节只定义未来 policy-transfer 的候选信息流与归因要求，不构成已冻结的 π0.5 实现方案。具体结构、loss、data mixing、loader、sampler、budget 与 checkpoint 只能在 [[数据构造/数据构造方案#第三部分：多任务训练混合与 π0.5 接入协议（Deferred）|合并总方案的 π0.5 接入部分]] 中冻结；当前保持 `policy_protocol_status: deferred_not_started`。C0–C6 作为未来必须满足的归因约束保留，不表示已经选择某种训练架构。

```mermaid
flowchart TB
    subgraph Policy["正常策略分支"]
        O1["当前图像 + 状态 + 指令"] --> S["共享 VLM / LoRA / Adapter"]
        S --> A["Action expert"]
        A --> LP["L_policy"]
    end

    subgraph Privileged["训练期特权意图分支"]
        F["未来动作 A⁺"] --> C["Future-action compressor"]
        O2["当前图像 + 状态<br/>屏蔽答案指令"] --> S
        C --> S
        S --> I["Intent head"]
        I --> LI["L_intent"]
    end

    LI -.梯度进入共享参数.-> S
```

必须通过梯度检查确认 $\mathcal{L}_{intent}$ 真正更新了策略会保留的共享参数。

但“梯度进入共享层”只是必要条件，不是部署收益的充分条件。模型仍可能把 future-action 语义限制在只有 future token 才激活的路径中；部署移除 future encoder 后，正常 policy 未必能读取到它。

因此 independent probe 只作为 A/B 阶段的信息可读性诊断；进入 C 阶段后，至少按以下矩阵比较：

| 编号 | 训练条件 | 是否使用 future | 归因作用 |
|---|---|---:|---|
| C0 | policy-only | 否 | 控制基线 |
| C1 | policy + structured-intent loss，输入为部署可见的 $(o,s,\ell)$ | 否 | 普通结构化语义辅助 |
| C2 | policy + text-goal latent alignment | 否 | 普通目标语言对齐 |
| C3 | shared future-action intent objective，无显式 alignment | 是，仅训练期 | 检查共享目标是否迁移 |
| C4 | future-aware teacher → deployment-path alignment | 是，仅训练期 | 候选 privileged transfer |
| C5a | shuffled／wrong-future shared objective | 伪 future | 与 C3 架构匹配，排除 shared auxiliary 本身 |
| C5b | shuffled／wrong-future teacher alignment | 伪 future | 与 C4 架构匹配，排除 alignment 路径本身 |
| C6 | equal-capacity nonsemantic auxiliary | 否 | 排除等容量正则化效应 |

C1／C2 只属于控制迁移阶段，不能把正常指令重新放进 A/B 的 future-value probe。各条件要尽量匹配 target 粒度、head／adapter 参数量、训练步数与数据量。C3 必须相对 C1、C2、C5a、C6，C4 必须相对 C1、C2、C5b、C6 有预注册且稳定的增益，才支持相应架构下的“future-action-specific transfer”；若仅优于 C0，最多说明额外语义／辅助训练有效。

候选形式为：

$$
z_T=E_T(o_t,s_t,A^+_{t,H})
$$

$$
z_S=E_\pi(o_t,s_t,\ell)
$$

$$
\mathcal L
=
\mathcal L_{policy}
+
\lambda_1\mathcal L_{intent}(z_T,y)
+
\lambda_2\mathcal L_{align}
\left(\operatorname{sg}(z_T),z_S\right)
$$

这里 student 必须读取正常任务指令 $\ell$，且 action expert 必须实际消费 $z_S$；否则同一 $o_t,s_t$ 对应多意图时，image-only student 没有信息选择正确分支。`stop-gradient`／EMA teacher、MSE、对比对齐都只是候选实现，要与 shared-no-alignment、无 future 的 structured-intent／text-goal 语义基线、shuffled-future alignment 和等容量非语义辅助严格比较。

### 8.3 部署阶段

部署仍然是：

```text
当前视觉 + 当前机器人状态 + 正常任务指令
                ↓
             π0.5 policy
                ↓
           未来动作 chunk
```

训练期的：

- future-action encoder；
- compressor；
- intent head；

可以移除。部署时不输入 oracle future action，也不要求先生成自然语言意图再执行。

### 8.4 关于 teacher–student 的审慎结论

“future-action teacher → deployment student”可以作为后续 privileged learning 方案，但不能直接写成当前主定义或未经实验验证的唯一主方法。

原因是本数据刻意让同一 $o_t,s_t$ 对应多个意图，因此：

$$
p(y\mid o_t,s_t)
$$

本来就不应是单一答案。若强迫 image-only student 精确复现某个 future-conditioned teacher，可能产生互相冲突的监督。

可行的扩展包括：

- student 同时读取正常任务指令；
- 蒸馏候选意图分布，而非单一 one-hot；
- 只蒸馏共享动作语义表征；
- 把 teacher–student 作为与“共享联合损失”分开的消融。

在机制 A／B 通过并完成 π0.5 信息流审计前，它是候选 transfer mechanism，不是已决定路线。其价值必须由部署输入不变的 rollout 验证。

> [!note] π0.5 论文经验与开源实现边界
> [π0.5 论文](https://arxiv.org/abs/2504.16054) 的 implicit-HL ablation 表明：训练中包含 subtask prediction 数据、部署时不显式做高层推理，仍可能获得部分收益。这支持“共享联合损失值得先做”，但不证明本项目 future-action auxiliary 必然迁移。
> [openpi 官方 README](https://github.com/Physical-Intelligence/openpi) 截至 2026-07-31 仍写明公开 π0.5 训练／推理只支持 flow-matching head；subtask prediction 的公开接入状态还需按实际 commit 审计。因此 shared loss、latent alignment 与 high-level decoding 都要视为本项目需要自行实现和验证的模块。

---

## 9. 核心实验、当前状态与可证伪结论

整项研究拆成彼此不能替代的假设；当前 Mouse MVP 的状态如下：

| 假设 | 当前状态 | 当前最强结论 | 不能推出什么 |
|---|---|---|---|
| A1：future 内容是否提供额外目标信息 | **通过核心诊断** | 在 Mouse 三目标、4-root certified envelope 内，future／step-delta 支持目标识别、跨路径一致性与 replacement switch | 不能推出时间顺序、正式泛化或控制提升 |
| A2：任务与模型是否具有顺序可识别性 | **S2 上未解决** | Mouse 对照未稳定下降，且其标签可能天然 order-insensitive；需要 S3/S4 裁决 | 不能声称长动作／程序顺序理解 |
| B1：正式 anchor-based $H/P$ reveal | **未完成** | 当前只有 branchpoint-aligned $L$ 诊断 | 不能报告 $H_{\mathrm{reveal}}$ |
| B2：最小 $K$／semantic compression | **未开始** | 尚无压缩实验 | 不能报告 $K^\*$、footprint 或 encoded-rate 优势 |
| C：是否反哺部署 policy | **未开始** | 无 π0.5、rollout 或 policy-transfer artifact | 不能用 probe accuracy 代替 |
| 任务族泛化 | **未证明** | 有效独立 root 数为 4，只覆盖 Mouse 三目的地 | 不能称 scene-family／task-family formal generalization |

A1 的 `core pass` 不会自动点亮 A2。A2 与正式 B1 通过后，才有资格投入 B2；只有 A/B 都通过后才投入 C。任一阶段失败都是合法结果，必须如实保留。

### 9.1 机制问题

> 在严格相同的当前图像与机器人状态下，raw／近似无压缩的正确未来动作是否比 visual/state-only 更能识别意图？把 future A 替换成同 group 的 future B 后，预测是否随 target 一起从 intent A 切换到 intent B？

若不能，不能声称未来动作携带了被模型利用的意图信息。若只在 seen planner 上有效、换同意图轨迹就失败，则更可能是轨迹指纹而不是语义理解。

### 9.2 Horizon 问题

> 在不同共享前缀长度 $P$ 下，意图性能如何随未来覆盖 $H$ 变化？哪个动作阶段开始暴露意图？

第一层先对每个 comparison cohort $c$ 安全地报告：

$$
\mathrm{IntentScore}(H\mid P=P_c,c)
$$

以及在**固定 candidate universe、固定 branch-balanced benchmark sampling protocol** 下，相对无 future 条件的 branch NLL reduction：

$$
\Delta_{\mathrm{NLL,bal}}(H;c)
=
\mathrm{NLL}_{bal}(H=0;c)-\mathrm{NLL}_{bal}(H;c)
$$

这里的 `balanced` 是人为控制的评测采样分布，必须记录 `target_distribution_basis: balanced_candidate_protocol`；它不是自然世界的真实 intent prior，也不称为互信息。set-marginal loss／compatible-set probability mass 因为 target set 随 H 收缩，不能直接代入上述差分。跨 cohort 按 $P$ 的汇总首先只是分层描述；只有共享 `matched_p_family_id`、主要难度因素已匹配且原则上只改变共同前缀长度时，才直接比较 $P$ 或解释 $H-P$ 差异。`prefix_type` 不同的 cohort 分表。

在上述边界内，还可报告：

$$
\Delta(H,K\mid P)
=
\mathrm{Score}(H,K\mid P)-\mathrm{Score}(H=0\mid P)
$$

以及达到完整未来性能某一预注册比例所需的最小 horizon，例如：

$$
H_{90}(P)
=
\min\{H:\Delta(H,K\mid P)\ge 0.9\Delta(H_{full},K\mid P)\}
$$

具体比例与容差应在看测试结果前确定。

### 9.3 Compression 问题

> 在相同共享前缀 $P$ 和未来覆盖 $H$ 下，不同压缩方法在固定 token 预算 $K$ 下保留多少意图信息？

主比较必须匹配：

- 同一训练数据；
- 同一 $H$；
- 同一 $P$；
- 同一 $K$；
- 相近参数与训练步数；
- 相同视觉／状态输入；
- 相同测试分组。

并同时报告 $K$、token 维度／词表、representation footprint 与计算成本；具有可复核实际／估计码长时再报告 encoded rate。“固定 K”本身不足以代表等容量。

### 9.4 复杂 grounding 问题

> 模型是否把未来动作与当前画面中的具体对象、参照物和操作顺序绑定，而非只读取绝对末端位置或夹爪模式？

必做对照：

- candidate-only：只读取候选程序，检查程序长度、op／constraint 频率、模板与候选先验；
- 对象位置置换；
- 同类 distractor；
- 参照物位置变化；
- current state + future action（no vision）；
- 纯 future-action-only；
- endpoint-only；
- wrong-scene future：能映射到当前 candidate 的合法 replacement 与 scene-incompatible OOD 分账；
- 同场景下 future replacement，并检查预测是否切换到 replacement intent。

对 candidate-ranking 输入应进一步拆成：`candidate-only`、`current+candidate (H=0)`、`state+future+candidate (no vision)`、`future+candidate (no current)` 与 `current+future+candidate`。全部使用同一冻结 candidate universe 和共享 scorer；候选步数、文本／序列长度、op 频率、constraint 比例与显示位置要平衡或显式做 leakage probe。

### 9.5 反哺控制问题

> 在部署输入完全相同、训练预算相近的条件下，共享的 future-action intent 目标是否改善正常策略？

至少比较：

- policy-only；
- policy + structured-intent loss，输入只含部署可见的 current／instruction，不使用 future；
- policy + text-goal latent alignment，不使用 future；
- future-action intent probe 但不回传共享层；
- shared future-action intent、无显式 alignment；
- future-action teacher → deployment-path alignment；
- shuffled／wrong-future shared objective（架构匹配 shared future objective）；
- shuffled／wrong-future teacher alignment（架构匹配 future-teacher alignment）；
- equal-capacity nonsemantic auxiliary。

要把收益归因于 **future-action-specific supervision**，future 条件必须相对两个无 future 的普通语义基线、与自身架构匹配的 shuffled／wrong-future control、以及等容量非语义辅助都达到预注册优势；否则只能说“增加语义或辅助损失有帮助”。

若 intent probe 明显有效但 rollout 没有稳定增益，正确结论是：

> 未来动作中的意图可被读取，但尚未证明这种训练信号能反哺控制。

### 9.6 主要指标

优先使用结构化指标，但两种输出模式必须分表：

- **机制主任务：same-group candidate retrieval/ranking**
  - candidate-only prior 与 permutation-consistency；
  - compatible-set probability mass／set recall；
  - 同一 current group 内的 candidate ranking；
  - singleton-eligible horizon 的 Top-1 accuracy／Recall@$k_{\mathrm{ret}}$（检索 cutoff 不使用核心压缩符号 $K$）；
  - replacement prediction-switch rate；
- **泛化副任务：global structured program decoding**
  - 完整结构化意图 exact match；
  - `num_steps`、每个 step 的 `op/object/relation/reference` 与 `constraints` 准确率；
  - sequence edit distance；
  - 未见 object-role／intent composition 的 step-slot 与 exact-match；
- 两类任务共同报告：
  - 预测置信度与校准；
  - 每 cohort 的 $\mathrm{IntentScore}(H\mid P,c)$、按 `prefix_type` 分层的曲线，以及 matched-P family 内的直接对照；
  - 固定 $P$ 的 `H × K` 性能—计算曲面；
  - same-intent cross-trajectory retrieval；
  - held-out test group 内 seen-planner vs unseen-family paired intent accuracy；
  - time-warp／path-perturbation invariance；
  - endpoint 差异、valid-reorder switch、invalid/OOD uncertainty 与 wrong-scene 分账指标；
  - 最终策略 rollout 成功率与任务进度。

不同 H 的 compatible-set size 不同，不能只用 raw set recall 横向比较并宣称 future 增益。歧义 horizon 主要看 set probability mass、相对预注册 target distribution 的 proper score／KL、entropy 与校准；task-tree set 收缩为单例后才比较 Top-1、branch NLL 与 prediction-switch。

自由文本流畅度与注意力图只能作辅助展示。

---

## 10. 这个 idea 最可能成立的贡献结构

当前不预先宣称 novelty 已被文献检索证明。第一阶段贡献应围绕受控 H/P/K 机制，而不是先建设庞大 benchmark：

1. **受控问题与数据协议**
   同一当前观测对应多个行为意图，每个意图又有多条成功轨迹实现；用可控共享前缀 $P$ 延迟意图证据，并用 future replacement 验证输入依赖与预测切换。机制稳定后，这套协议才可能扩展为 benchmark。

2. **Future Action Horizon / Prefix Reveal**
   系统刻画意图信息随 $H$ 出现、增长和饱和的规律；不同 $P$ 先分层描述，只有 matched-$P$ family 才分析其受控改变如何推迟 reveal。

3. **Long-action Tokenization / Compression**
   在 raw future 价值已经成立后，固定 comparison cohort $c$ 及其 $H,P$，研究如何用少量 token／representation footprint 保留跨事件、跨子任务的意图证据；具有可复核实际／估计码长后再研究 semantic encoded-rate。

4. **对 VLA 控制的作用**
   在部署接口不增加 oracle 信息的前提下，检验该训练目标是否改善动作预测和 rollout。

其中前三项可以形成独立的诊断数据／方法价值；第四项必须由真实联合训练与 rollout 证明，不能从 probe 结果推断。

### 10.1 2026-07-31 最近工作核查与新颖性边界

根据本次对原始论文／官方仓库的核查，不能把贡献写成“首次输入未来动作理解意图”：

| 工作 | 已覆盖的相近部分 | 与本项目当前可防守差异 |
|---|---|---|
| [PRTS](https://arxiv.org/abs/2604.27472) | 当前多视角／本体状态 + FAST-tokenized $a_{t:t+H}$，构造 state-action 表征并与语言目标做双向对比；使用 role-aware mask | 未见其系统控制 same-current multi-intent、严格 $P$、compatible-set、H/P reveal 与 same-intent multi-realization 协议 |
| [LACY](https://arxiv.org/abs/2511.02239) | action-to-language 与 language-to-action 联合训练 | 不等同于本项目的受控未来可识别性与 H/P/K 测量 |
| [FutureVLA](https://arxiv.org/abs/2603.10712) | 用 future-aware joint visuomotor embedding 对齐下游 VLA 表征 | 提供 transfer 机制先例，但不是 structured future-action intent identifiability 协议 |
| [MINT](https://arxiv.org/abs/2602.08602) | 用多尺度频域 token 区分 intent／execution 表征 | 更接近生成与迁移中的 action hierarchy，不直接回答 same-current prefix reveal |
| [Coarse-to-Control](https://arxiv.org/abs/2606.07107) | 预测 coarse action tokens 作为未来计划，再生成低层动作 | 是前向 plan→action，不是将真实未来作为特权输入逆推可验证目标 |
| [FAST](https://arxiv.org/abs/2501.09747) | DCT、量化、BPE 的动作 tokenization 与压缩—重构分析 | 应作为长动作压缩 baseline，而非本项目 novelty |

因此当前更稳妥的研究定位是：

> **Controlled Multi-Future Intent Identifiability and Semantic Compression**

即受控测量：

- identifiability；
- controlled ambiguity；
- prefix／event reveal；
- future-conditioned prediction consistency；
- footprint-aware semantic compression；
- 显式量化／编码条件下的 semantic rate–distortion。

这是截至 2026-07-31 的非穷尽核查结论，不等于完整 novelty search 已结束。论文定稿前仍需系统检索，并逐项复现实验设置。

---

## 11. 当前实证状态（截至 2026-08-20）

> [!success] 阶段总状态
> Mouse 三目标受控多未来数据链与独立 root 的 core diagnostic transfer 已跑通；动作时间顺序理解、正式 $H_{\mathrm{reveal}}$、压缩和 policy transfer 尚未成立。

```text
status = pass_independent_root_core_temporal_unresolved_v1
accepted roots = [g7, g8, g11, g12]
effective root N = 4
core passing L = [2, 4, 8, 16, 32, 64, 128, 256]
temporal contrast passing L = []
formal_generalization_claim = false
h_reveal = null
compression_or_policy_transfer_started = false
```

### 11.1 已完成的数据与证据链

| 项目 | 已验证结果 |
|---|---:|
| accepted root groups | 4 |
| intents / root | 3 |
| realizations / intent | 2 |
| formal raw trajectories | 24 |
| 250 Hz action steps | 55,394 |
| raw HDF5 总字节 | 641,455,140 |
| receipts / verifiers | 24 / 24 |
| derived views | 144 |
| 四视角 MP4 | 24 |
| final checkpoints | 27 个 fixed-last |

四个 accepted roots：

| root | 当前角色 | raw | PC cohort 的 $P$ |
|---|---|---:|---:|
| `g_000007` | development；g6 recovery representative | 6 | 1154 steps / 4.616 s |
| `g_000008` | development；独立 root | 6 | 1154 steps / 4.616 s |
| `g_000011` | 一次性 adjudication root | 6 | 1151 steps / 4.604 s |
| `g_000012` | 一次性 adjudication root | 6 | 1157 steps / 4.628 s |

每组固定为：

```text
br1 / br2 → mouse on gray pad
br3 / br4 → mouse on electronic scale
br5 / br6 → mouse on display stand

odd branch  → r_pc
even branch → r_inv
```

三个 `r_pc` 进入严格 `prefix_controlled` cohort；每个 intent 的 `r_pc+r_inv` 进入独立 `trajectory_invariance` cohort。144 个 derived views 不等于 144 个独立样本；主要统计单位仍是 4 个 root。

### 11.2 已解决的工程事实

- primary future stream 已冻结为 250 Hz、26 维 `controller_effective_setpoint_v1`；
- raw 时间合同已冻结为 `N actions / N+1 states`；
- command、planner target、drive readback、realized state 与 verifier truth 已分流保存；
- current RGB／state 每个 root 只保存一次，六个 branch 共享同一 ref/hash；
- candidate universe 在主 planner rollout 前冻结，task feasibility 与 planner solvability 分账；
- failure、attempt budget、recovery lineage、GPU pre/post 与 orphan audit 均保留；
- branch/retry 的严格物理边界已收敛为 `fresh-scene reconstruction + canonical anchor contract`。

> [!important] 为什么最终采用 fresh scene
> Mouse MVP 实测发现，同一 scene 中反复 rewind 无法可靠清除 contact、sleep 与 solver 历史；wake、reapply、decontact 和重复 restore 都不足以证明 branch-history invariance。因此每个关键 branch／retry 使用新的 local scene，独立恢复并验证同一 canonical anchor，执行后关闭 scene。这个结论是当前 RoboTwin/SAPIEN 实现中的工程选择，不宣称是所有模拟器唯一可行方案。

### 11.3 模型诊断是怎样推进的

1. **Tiny v1**：current-only 为 33.3%，raw future 与 endpoint-only 都是 53.3%，strict replacement switch 为 0%；判定为 endpoint trap hard fail。
2. **Suffix/delta**：step-delta 显著减小跨 root absolute offset，但 g7↔g8 双fold/seed/controls 没有稳定全过。
3. **视觉路线**：top-1 grounder、proposal-set、patch embedding 逐层诊断，识别出 root-specific visual shift；旧失败 run 全部保留。
4. **独立 root 裁决**：最终 shared scorer 只在 g7+g8 训练并拟合 normalization；g11+g12 不参与 representation、hyperparameter、checkpoint 或 threshold 选择。冻结后一次性评测 9 个 $L$ × 3 seeds，共 27 个 fixed-last checkpoints。

最终，网格中的 $L\in\{2,4,8,16,32,64,128,256\}$ 均由三个 seed 在四个 root 上同时通过：

- PC natural 识别；
- 同 intent 的 `r_inv`；
- 六个有向 future replacement；
- future／vision／semantic mask；
- candidate cycle 与 candidate permutation。

`L=1` 的 PC/replacement 仍通过，但 g11 `r_inv` 未在三个 seed 上全部满分，因此不属于完整 core passing horizon。

### 11.4 当前支持的结论

1. 可审计的 same-current、multi-intent、multi-realization 数据协议已经落地；
2. future／step-delta 内容在 Mouse 三目标 certified envelope 内具有目标诊断价值；
3. future replacement 后预测能够随真实 replacement future 正确切换；
4. 同意图的另一条真实路径仍能保持目标判断；
5. current visual embedding 对跨布局解释动作方向是必要的；
6. 上述 core diagnostic 能迁移到两个未参与训练的新 root。

### 11.5 当前不支持的结论

1. 未证明模型理解动作时间顺序；
2. `L=2` 不能写成 `H_{\mathrm{reveal}}=2` 或“8 ms 后出现意图”；
3. 未完成从真实 root anchor 开始的正式 $H/P$ reveal；
4. 有效 root $N=4$ 不等于 task-family／scene-family formal generalization；
5. 144 个 derived views 不能当成独立样本；
6. 当前 pilot 是 $R=2$，正式机制可行任务仍建议逐步达到 $R\ge3$；
7. 尚无 $K^\*$、compression、encoded-rate 或 semantic rate–distortion 结论；
8. 尚未接入 π0.5，也没有 policy-transfer 或 rollout 提升；
9. g11/g12 已经完成并被查看过一次性 adjudication，后续不能再称为 untouched holdout；
10. “30%”仍只是规划口径，不是立即扩到 750／7,500 条的采集授权。

更完整的机器证据与路径见 [[数据构造/初步尝试 2026.8.25/成果复盘|成果复盘]]、[[数据构造/初步尝试 2026.8.25/简单尝试 2026.8.10 .md|实时日志]]与 [[数据构造/初步尝试 2026.8.25/受控多未来轨迹视频_g7_g8_g11_g12/四组数据与视频说明|四组数据与视频说明]]。

---

## 12. 已解决与仍未解决

| 项目 | 当前状态 |
|---|---|
| primary future stream | **已解决**：250 Hz、26 维 controller effective setpoint |
| raw 时间轴 | **已解决**：$N$ actions / $N+1$ states |
| restore／branch 边界 | **已解决**：fresh-scene reconstruction + canonical anchor |
| structured intent | **已解决于 Mouse MVP**：三个 `place(mouse, on_surface_of, destination)` program |
| candidate freeze | **已实现** |
| shared candidate-conditioned scorer | **已实现并通过 permutation Gate** |
| same-current branches | **已实现**：每 root 3 intents |
| pilot realization $R$ | **已实现为 2**：`r_pc+r_inv` |
| formal realization $R$ | **未达到**：仍建议可行任务 $R\ge3$ |
| PC / TI cohort | **已实现并分开** |
| future-content / replacement | **通过核心诊断** |
| cross-realization invariance | **通过核心诊断** |
| temporal-order dependency | **未解决** |
| 正式 anchor-based $H/P$ reveal | **未完成** |
| $H_{\mathrm{reveal}}$ | **null** |
| $K$/compression | **未启动** |
| global structured program decoding | **未实现** |
| 多任务族／scene-family 泛化 | **未证明** |
| π0.5 共享位置与训练 | **未解决／未启动** |
| policy transfer / rollout | **未启动** |
| 下一批 F1–F4 数据方案 | **`v1_2` protocol review 已完成、采集未开始**：40 accepted roots／360 formal raw trajectories，另有 16 ordered reserve planned slots |

> [!warning] 当前科学瓶颈
> 现在最主要的缺口不是“模型还不能区分 pad/scale/stand”，而是尚不能区分两种解释：模型没有学到顺序，或 Mouse S2 目的地标签本来就近似 order-insensitive。继续只提高 natural-future accuracy、或者强求现有 S2 必须击败 shuffle，都不会自动解决这个问题；需要现有 S2 诊断与新的 S3/S4 顺序敏感任务共同裁决。

---

## 13. 下一阶段正式数据方案：四类 Controlled Multi-Future 场景族

> [!important] 本节只保留研究摘要
> 本节负责说明为什么需要 F1–F4、四类 family 的科学分工、phase-1 规模、阶段 Gate 与停止线。场景角色、candidate programs、realization、verifier、split、reserve roots、文件结构、采集流程、Schema、实现映射和验收清单只在 [[数据构造/数据构造方案|`controlled_multi_future_f1_f4_v1_2` 数据构造方案]] 中维护；本文不再复制执行规范。

> [!warning] 当前状态
> 截至 2026-08-26，新方案完成 `v1_2` protocol review 修订，但 `implementation_status = not_started`。Stage 0 仍被 code/asset/verifier mapping 与 `pilot_attempt_budget_v0` 阻塞；没有生成 F1–F4 新轨迹，也没有授权 Stage 0、Stage 1、formal collection、compression 或 policy training。

### 13.1 为什么下一批不能只是扩展 Mouse 目的地

Mouse S2 已支持 future-content、future replacement prediction-switch 与同意图跨路径一致性，但 endpoint、净位移或无序动作统计可能已经足够，当前仍是：

```text
future-content core pass
temporal-order unresolved
formal anchor-based H/P not started
h_reveal = null
```

下一批只回答四个互补问题：

1. 操作 current 图像中的哪个具体对象？
2. 同一对象对应哪个目标—关系 program bundle？
3. 相同起终态和相同动作原语 multiset 中，细粒度事件顺序是什么？
4. 相同对象、子任务集合和最终世界状态中，高层操作顺序是什么？

F1/F2 负责 future content 与 visual grounding；F3/F4 负责 Temporal Identifiability。继续只增加目的地数量不能填补时间顺序证据缺口。

### 13.2 四个冻结 family

| Family | 一句话定义 | 主要结论职责 |
|---|---|---|
| F1：近邻同类对象选择 | 三个近邻同类对象分别进入同一公共容器；对象身份与空间位置跨 root 轮换 | 具体对象 grounding，排除固定方向标签 |
| F2：目标—关系组合 | 同一主对象分别执行 `box+IN / scale+ON / pot_or_stand+BESIDE` | object–target–relation bundle grounding；**不声称 relation/facility 解耦或组合泛化** |
| F3：细粒度动作顺序 | `VVHH / VHVH / VHHV`；V/H 各两次、起终态相同，并共享第一个 V | table-frame 低层事件顺序；endpoint 与 action multiset 应不足 |
| F4：高层子任务顺序 | 先完成 common X 子任务，再执行 `ABC / ACB / BAC`；最终 object-slot mapping 相同 | 多对象高层 program order |

F3 的首批物理轴固定为 table frame 的 `±z`（V）与 `±x`（H）；模型输入仍是 effective setpoint，事件 success 必须由隐藏的 realized EEF／bottle motion 与 grasp continuity 验证。

### 13.3 Phase-1 规模、split 与采集阶段

正式机制数据固定为：

| 项目 | 数量 |
|---|---:|
| families | 4 |
| accepted roots / family | 10 |
| intents / root | 3 |
| realizations / intent | 3 |
| formal accepted roots | 40 |
| formal raw trajectories | 360 |

Stage 2 还预注册每 family 4 个 ordered reserve planned slots，共 16 个；未激活 reserve 只有 slot/seed/generator/rank，`candidate_freeze_status=pending_activation`，不能伪造 candidate hash。它们不进入 formal denominator，只有 active slot 失败时才按冻结顺序继承 split／difficulty 并启用。

每 family 的 phase-1 split 为 `5 train / 2 validation / 3 test`，总计 `20/8/12 roots` 与 `180/72/108 trajectories`。难度与 split 交叉分配为：

| Split | clear | medium | crowded |
|---|---:|---:|---:|
| Train | 1 | 3 | 1 |
| Validation | 0 | 2 | 0 |
| Test | 1 | 1 | 1 |

该规模只称 `phase-1 formal mechanism dataset`；即使每 family 有 3 个 test roots，也不等于强 task-family generalization。

采集阶段固定为：

```text
Stage 0：
  先冻结 pilot_attempt_budget_v0
  四个 Pilot root A 各先采 3 个 r_pc
  = Stage 1 累积数据中的前 12 条

Stage 1：
  Pilot root A = r_pc + r_inv_path
  Pilot root B = r_pc + r_inv_motion
  每 family 12 条，四个 family 累积总计 48 条
  Stage 0 后只继续补 36 条，不是总计 60 条

Stage 2：
  先冻结 40 primary + 16 reserve planned_root_slot_spec；
  40 active slots 形成 candidate_frozen_root_spec，
  未激活 reserve 保持 pending；
  split × difficulty、budget、verifier、H-view、
  source lock、F1–F4 code/asset mapping、
  mechanism model/eval procedure

Stage 3：
  前置 Gate 通过并获得明确授权后，
  才生成／补齐并 seal 40 roots / 360 trajectories
```

candidate 的唯一合法顺序是：

```text
frozen planned_root_slot_spec
→ deterministic provisional scene/root
→ three provisional structured programs
→ task/physical feasibility audit
→ all three feasible
→ freeze candidate universe/hash + task tree
→ freeze canonical prefix
→ formal planner rollout
```

freeze 后 planner 失败不能静默删除 candidate；必须保留失败证据并按预注册 stop/reserve 规则处理。

### 13.4 Family-specific controls 与标签语义

- **F1/F2/F4**：no-vision 相对完整输入明显下降是 visual grounding hard Gate。
- **F3**：no-vision 只作诊断，不是失败条件；V/H 顺序本身可以足够识别程序。
- **F3 valid reorder**：固定包含 shared-first-V 的 prefix，只重排后三个 suffix blocks并同步切换 target。
- **F4 valid control**：真实成功分支 program replacement 必做；strict neutral-to-neutral block reorder 只有 continuity + fresh-scene replay + verifier 通过时使用。
- **Invalid/OOD shuffle**：重排后不属于 candidate universe 时，不能沿用原 one-hot；只作 reject／entropy／margin／OOD diagnostic，未预注册 reject head 时不决定 `temporal_identifiability_pass`。
- **Wrong-scene future**：合法可映射 replacement 与 scene-incompatible OOD 必须分账。
- **`r_inv_motion`**：执行臂和 250 Hz primary stream 不变，只改变速度、event duration、order-preserving time-warp、幅度与轻微停顿。
- **`r_inv_path`**：同样固定执行臂和 250 Hz primary stream，只改变接近／抓取／运输路径与 planner seed。
- **`r_inv_arm`**：只作可选 OOD/invariance diagnostic，不计入固定 $R=3$。
- **F2 verifier**：使用互斥的 `inside_volume / top_surface_region / beside_annulus`，避免通用几何谓词重叠。

### 13.5 当前停止线

固定研究顺序仍为：

```text
future content
→ task-conditioned temporal identifiability
→ anchor-based H/P
→ K / semantic compression
→ policy transfer
```

在 F3/F4 Temporal Gate 通过前，不启动 $K$-token compression、FAST/K-query 正式比较、π0.5 联合训练或 policy rollout。

360 条数据只回答 future content、temporal order 与 $H/P$ reveal。phase-1 模型、representation、normalization、checkpoint、root-level statistics 与 test seal 必须在 [[数据构造/数据构造方案#第二部分：F1–F4 机制模型训练与评测协议（Deferred）|合并总方案的机制评测部分]] 中冻结；它也不是完整的 RoboTwin2 50-task π0.5 混合训练集，policy/intent loss、官方 episode mixing、sampler 权重、structured-program tokenization 与 π0.5 loader 必须以后在 [[数据构造/数据构造方案#第三部分：多任务训练混合与 π0.5 接入协议（Deferred）|合并总方案的 π0.5 接入部分]] 中冻结。

详细执行只见：[[数据构造/数据构造方案|数据构造方案]]。

---

## 附录：设计审阅历史

> [!info] 附录定位
> 三轮 GPT 审阅的完整原文已经独立归档，不在 canonical 主入口中重复维护。发生冲突时，以本文正文冻结定义、formal artifact 和更晚 append-only 机器记录为准。

- [[Idea/归档/2026-08-25_其余Idea材料/Gpt建议|GPT 第一轮建议]]
- [[Idea/归档/2026-08-25_其余Idea材料/Gpt二轮建议|GPT 第二轮建议]]
- [[Idea/归档/2026-08-25_其余Idea材料/Gpt三轮建议|GPT 第三轮建议]]

### 冻结设计决策简表

| 决策 | 当前口径 |
|---|---|
| 时间方向 | 相对 current anchor 的 future action，不是 past-action recognition |
| 数据单位 | same-current multi-future root group |
| 多实现 $R$ | 保留；pilot 已实现 $R=2$，正式机制仍建议 $R\ge3$ |
| compatible set | 使用 input-observable task tree；oracle 只审计 |
| candidate scorer | shared candidate-conditioned；禁止 group-local fixed class head |
| candidate freeze | task feasibility 后、primary rollout 前 |
| split | whole root／更保守 scene family 原子划分 |
| replacement | prediction-switch／input-dependence，不作因果证明 |
| 下一批数据 | `controlled_multi_future_f1_f4_v1_2`；F1–F4、40 accepted roots／360 formal raw trajectories，另有 16 ordered reserve slots；当前仅 design revised、采集未开始 |
| 表示与压缩 | 先固定 action representation，再比较 $K$/footprint |
| 研究顺序 | future content → task-conditioned temporal identifiability → anchor-based $H/P$ → $K$ → policy |
| teacher–student | 仍是后续 transfer 候选，不是当前主方法 |

> [!important] v1 设计冻结时的历史状态
> 2026-07-31 冻结设计时，服务器动作语义、fresh-scene 边界、正式数据和模型诊断都尚未完成；当时的下一步确实是先实现 2–5 个 root groups。这只是历史状态，不是当前进度。
>
> 截至 2026-08-20，Mouse MVP 的 4 个 accepted roots、24 条 formal raw trajectories、144 个 derived views、24 条 MP4 与独立 root 小模型诊断均已完成。当前机器状态、仍不能声称什么和下一阶段以正文第 11～13 节为准。
