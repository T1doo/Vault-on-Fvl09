# 完整用户Goal来源

URL: https://chatgpt.com/s/t_6a9d9c54d9188191bd7bfbbf0579635c

公开分享页可见消息共 1 条；完整解析role/content，包含末尾附加建议。原filecite为分享对话内部引用，不冒充本地已读证据。

## assistant

可以。**这次应该把任务从“再修一个问题”升级成“在明确边界内，连续完成四类任务和 pilot 数据”**，否则即使用了 Goal，Codex 还是会被旧的“一次微门、一次审批”规则卡住。

我刚核对了仓库，当前仍是 `2b43b541c3ae8d9b1d8a8f396225dc50601786ec`：F3 抬升计划已经成功但尚未实际执行，F2 还缺持物到释放的实际模型切换，F4-B 还缺完整运行预算；已验收数据为 **6 个根、27 条 raw，18 个 pilot 候选格有完整证据**。fileciteturn483file0L2-L2 fileciteturn487file0L2-L2

**我建议这次 Goal 的终点设为：**

> **F1–F4 全部贯通，补齐并验收 48 条 pilot 输入数据，完成数据完整性与批量采集链路检查，准备好正式 360 条的生产方案；暂不启动正式 360 和模型训练。**

这个目标比“只修 F2/F3”更完整，也比“直接无限跑到 360 条”为稳妥。下面是可以直接交给 Codex 的完整任务书。**其中的阶段推进、重试和总预算，是这次建议采用的新任务范围；由你将正文作为任务指令发给 Codex 后执行，不是要求它擅自绕过管理员或工具权限。**

---

# 给 Codex 的连续 Goal：四族贯通与 48 条 Pilot 数据完成

## 0. 总目标与工作方式

**将本任务设置为当前持续 Goal。**

目标不是完成一份计划、通过一批 CPU 测试或修复一个函数，而是：

1. F1/F2/F3/F4 均具备真实成功的完整三分支采集能力。
2. 完成四族各两个 pilot 根的输入数据，共 **8 个 pilot 根、48 条有效轨迹**。
3. 验证数据来源、current、anchor、前缀、真实 realization、family verifier、raw/video、计数与清理。
4. 用一次冻结版本的连续采集验证运行链路，不再依赖逐条改代码。
5. 交付可继续执行正式生产的代码、场景生成规则、预算与 manifest 草案。
6. 本任务不启动正式 360 条、不训练模型、不宣称科学机制或泛化能力已经得到证明。

普通代码修复、测试、版本发布、范围内的诊断与重试，由你自主推进。**不要在“CPU 已完成，等待 GPT 再批准下一个 helper”处停止。**

若 Goal 功能需要简短目标文本，使用：

```text
在明确的科学约束、共享服务器安全规则和累计资源预算内，连续完成
CVPR 项目 F1–F4 的采集实现、真实验证和必要修复，补齐四族八个
pilot 根共48条真实输入轨迹，完成独立验收与连续采集检查，并交付
正式360条生产方案。不得以计划完成、CPU测试通过或单次规划成功
代替目标完成；不得伪造轨迹、放宽物理验收或绕过安全限制。
```

---

## 1. 启动时读取当前事实，不重新翻译全部历史

以以下提交作为已知基线：

```text
2b43b541c3ae8d9b1d8a8f396225dc50601786ec
```

启动时检查最新 `origin/main` 与服务器实际工作树。若已有更新，先读取新增终端并计算差异，避免重复运行已经完成的任务。

优先读取：

```text
GPT_HANDOFF_SUPPORT_MODEL_AND_LIFT_PLAN_PASS_20260906.md
STAGE1_READINESS_SUPPORT_MODEL_LIFT_PLAN_PASS_20260906.json
F3_SUPPORT_AWARE_PHYSICAL_VALIDATION_PROPOSAL_V1_20260906.json
F4_B_ACTUAL_ENTRY_BUDGET_GAP_REVIEW_20260906.md
数据构造方案.md 中的阶段、realization、验收与 split 定义
当前实际生效的 AGENTS.md
```

然后沿**实际调用链**读取对应源码。不要把所有历史报告、巨大 trace 和全部版本重复塞入上下文。

当前起点是：

| Family | 当前可复用成果 |
|---|---|
| F1 | 五个 development 根、21 条 raw；其中 pilot A/B 所需的两组六格已有证据 |
| F4-A | 一个 development 根、六条 raw；原收据恢复与后续 path 变体均已验收 |
| F2 | 新内移布局 CPU 检查通过；实际 carry/release 模型与新布局规划尚待完成 |
| F3 | 新抓法已完成受支撑闭爪保持；保存状态下支撑模型与抬升规划通过；尚缺实际离台验证 |
| F4-B | 新布局已提出；实际入口预算未完整冻结 |

这些是当前机器记录中的状态，不得把尚未执行的步骤当成成功。fileciteturn487file0L2-L2

---

## 2. 明确最终完成标准

### 2.1 数据矩阵

每个 family：

```text
Pilot A：
3 intents ×（r_pc + r_inv_path）= 6 条

Pilot B：
3 intents ×（r_pc + r_inv_motion）= 6 条
```

四个 family 合计：

```text
4 × 12 = 48 条
```

已有 18 个候选格通过来源和协议一致性检查后，可以登记复用。**复用通过时，原则上只需补剩余 30 格，不重新采一套 48 条。**

全项目历史开发 raw 总量可以大于 48；**48 是选定 pilot 矩阵，不是整个数据目录只能有 48 个文件。**

pilot 与正式 root 的要求分开：pilot A/B 各六条，正式 root 才要求三种 realization 共九条。不要再次把 formal 9/9 前置到 pilot。主方案也将 48 条 mechanism pilot 与正式数据阶段分开。fileciteturn488file0L2-L8

### 2.2 每条有效轨迹必须满足

```text
真实 SAPIEN rollout，而非复制、伪造或旧 raw 重采样冒充
正确的 root / intent / realization 绑定
正确 current 与 anchor
对应前缀与事件合同
原 family 物理 verifier
独立 raw 和视频完整性检查
完整执行、规划、异常与 cleanup 记录
```

F3/F4 额外核对程序顺序与终态等价。

### 2.3 Goal 成功不等于科学结论成立

分别记录：

```text
pilot_input_data_accepted
collector_integration_verified
mechanism_checks_completed
model_experiments_completed
formal_collection_authorized
```

本任务要求前两项完成，并完成无需训练的结构与数据检查。

不训练模型，因此不能据此声称：

```text
未来动作一定提高模型能力
H_reveal 已测得
compression 已有效
泛化已经成立
```

若主方案的完整 Stage 1 还包含模型相关实验，保留为独立待办。**不要为了让状态变绿，把“48 条数据齐备”改写成全部科学 Gate 通过。**

---

## 3. 本次授权方式：总目标内自治，保留安全和科学底线

### 3.1 允许连续推进的范围

本 Goal 允许你自主完成：

- CPU 修复、接口集成与实际入口测试；
- 范围内 GPU 规划、模型核对和 SAPIEN 物理验证；
- F3 micro → shared-V → prefix replay → full root；
- F2 新布局规划 → 三关系完整 root；
- F4-B 新根与其 motion 变体；
- F2/F3 pilot A/B 及真实 path/motion 变体；
- 已有 pilot 输入的只读资格核对与显式登记；
- 失败分析、证据驱动的小范围实现调整和新版本重试；
- 完整预算推导、派生作业签发、运行、验收与 checkpoint。

**上述范围内，不再要求每个阶段都返回 GPT 获得新的单次批准。**

### 3.2 旧的一次性作业不“复活”

保留所有历史 consumption、failure 和禁止重发记录。

后续新运行应：

```text
引用本 Goal 的父任务范围
→ 使用新 run ID / 新 manifest / 新输出目录
→ 从本 Goal 累计预算扣账
```

不能把已消费作业改回未消费，也不能伪造新的“GPT 单次审批”。

在用户采用本任务书后，可将范围内子作业标为：

```text
ISSUED_UNDER_USER_GOAL
```

它表示用户给予了这一总任务的范围，不表示子作业已经被独立外审。

### 3.3 允许调整实现，但不允许改变研究问题

允许基于证据修改：

```text
局部布局与放置位置
不改变意图语义的目标朝向
抓取位置和接近姿态
中转路径与受控速度
planner 世界、附着物体与夹爪状态映射
源码接线、记录、验收发布顺序
```

修改前生成新版本 spec，保留父版本与原因；新结果只能归属于新版本。

不允许：

```text
删除 F2/F3，换两种简单任务后声称四族完成
将同一 root 的分支改成不同 current
把旧数组变形成“新的真实 rollout”
把错误关系或错误程序改标签算成功
只保留成功尝试而隐去失败分母
事后放宽物理、事件或终态验收阈值
降低摩擦/质量等物理真实性要求来强行成功
在物理引擎中焊接物体到夹爪
```

场景布局改变后，重新生成 current、anchor 和相关资格；不能沿用旧 hash 假装没变。

### 3.4 对“两候选确认”作一次明确的前瞻性调整

此前“必须两个不同抓取候选成功，才能继续实现后续任务”的开发门槛，不应继续使单个已成功 recipe 无法向后推进。

本 Goal 改为：

> **单一冻结 recipe 在两个独立 fresh scene 中真实通过抓取与微抬升，可以作为该 recipe 的研发确认，随后继续 shared-V 和 root。**

原来要求的“两种不同候选/资产成功”保留为**多样性与跨资产稳健性检查**，不能被两次同 recipe 成功冒充，但不阻塞单模板后续开发。

这是对后续开发准则的明确修改，不是重新判定旧失败，也不改变任何单次物理成功标准。最终仍要求 F3 的两个 pilot 根，且如实说明覆盖了哪些资产和布局。

---

## 4. 总资源预算：避免无限运行，也避免几十次 query 就反复停工

以下是**建议本 Goal 使用的资源护栏，不是实际需求估计，也不是完成时间承诺**：

| 项目 | 本 Goal 累计上限 |
|---|---:|
| 独立 IK 问题与轨迹规划问题合计 | 6,000 |
| fresh scene 创建尝试 | 240 |
| 进入机器人动作执行的场景 | 120 |
| 完整轨迹采集尝试 | 96 |
| 同时占用 GPU | 1 张 |
| 累计 GPU lease 占用 | 24 GPU 小时 |

这些额度包含失败、模型验证和恢复，不是必须用满。

规则：

1. 每个子作业启动前，从实际调用链推导最坏预算，并预留。
2. 子作业预算不能超过总剩余额度。
3. 批量求 N 个目标，按 N 个求解问题计数；不能包装成“一次调用”。
4. 固定并记录内部 seed 数、迭代和重试配置，不能隐蔽扩大搜索。
5. FK、碰撞检查与模型构造单列统计，GPU 用时仍计入累计占用。
6. unknown 不能写成 0。先尝试从独立账本核对；仍未知则暂停 GPU。
7. 全卡忙但尚未创建场景的调度拒绝不算物理失败，也不重置总预算。
8. 新会话、改文件名、换 runtime 版本都不能重置累计额度。
9. 总预算达到上限时，保存完整 checkpoint 并报告缺口，不自行追加。

不购买云 GPU、不创建新的收费服务、不绕过订阅或工具配额。共享服务器的管理员规则优先。

---

# 5. 工作线 A：优先让 F3 真正离台，并连续推进到完整 root

## A1. 先完成当前 support-aware 真实微门

现有保存状态已经通过 single/batch 检查与抬升规划，但没有执行动作；实际微执行入口也已接入当次支撑证据、当次规划和 post-lift 检查。应在此基础上修正，不再重写抓取系统。fileciteturn484file0L2-L2 fileciteturn486file0L2-L2

执行顺序：

```text
新场景与 current/anchor
→ trace 初始化
→ 当次 pregrasp
→ 原 full-window Gate
→ 当次 grasp
→ 原 full-window Gate
→ close 0.50
→ hold 250
→ 当次瓶子—对应 pad 的支撑证据
→ 当次 attached-bottle 和 pair-aware 模型
→ 当次 actual EEF +25mm 规划
→ 当前全部控制点的 native 几何筛查
→ 真实 lift
→ hold 50
→ 原 post-lift 验收
```

不得直接执行旧的 109 点，不要求新计划也恰好 109 点。

重点保留：

```text
20 mm 实际升高
50 帧离台确认
5 mm / 0.05 rad 相对漂移上限
原 selected-contact 与禁止碰撞判据
```

支撑 witness 必须绑定真正被排除的 pad actor/shape，不以任意 table 接触替代；full-window Gate 的真实能力仍是段后审查，不宣称已经实现逐步实时急停。

## A2. 成功后，继续 fresh-scene 重复确认

在相同 recipe 和标准下再独立执行一次，确认它不是一次偶然成功。

两次结果分别封存，不能复用第一次的：

```text
实际关节状态
支撑稳定布尔值
抓持变换
模型实例
规划 controls
```

若已有后续完整前缀运行包含完全相同且完整记录的微门，可作为第二次确认，不必额外重复相同实验。

## A3. 继续 shared-V，不再回来等单独批准

微门确认后：

1. 恢复适用于持物运动的完整环境碰撞检查。
2. 以实际抓持状态与中心构造 shared-V。
3. 保留已有事件语义、幅度与返回标准。
4. 验证瓶子真实跟随动作，而不是只看 EEF。
5. 验证返回中心、接触、抓持漂移与终态稳定。
6. 保存可复用的抓取—抬升—shared-V 前缀实现。

支撑接触例外不能长期延续到任意运输或 shared-V。模型近似导致误拒绝时，做有证据的 pair/phase 修订，不能整体关闭 pad/table。

## A4. 继续 prefix replay 与 full root

完成：

```text
1 次 canonical prefix 生成
2 次独立 fresh-scene 精确重放
```

通过后接入：

```text
VVHH
VHVH
VHHV
```

要求 shared first V、分支起点、原始动作字节、current/anchor 和事件边界均有证据。

完整 root 通过后不要停止，继续形成 F3 pilot A/B：

```text
A：r_pc + r_inv_path
B：r_pc + r_inv_motion
```

B 必须是真正的新 root，不能只复制 A 后改 ID。

## A5. 失败处理

每次按最早失败阶段处理：

```text
初始化 → 普通接线修复
目标/IK → 模型、姿态与可达性
接近/进入抓取 → 路径或终点接触
闭爪 → 抓持几何与控制
抬升 → 承重稳定
shared-V → 持物动作与返回
root → replay、程序或验收
```

不要把后续失败再次解释成已经解决的前置问题。

对于一个明确失败类别，最多推进三个有证据、预先冻结的修订版本。每个版本先完成 CPU/几何筛查，再执行必要的有限验证。相同确定性输入反复失败而没有任何修正，不算有效推进。

---

# 6. 工作线 B：完成 F2 放置模型、新布局验证和三关系 root

## B1. 先补真实 carry/release 状态切换

当前新内移布局与 binding 已通过 CPU 检查，缺的是实际 planner 中的持物/释放切换，不能把它继续表述为“新布局又失败”。fileciteturn487file0L2-L2

实际实现必须区分：

| 阶段 | 罐子 | 夹爪 |
|---|---|---|
| C→U | 附着碰撞几何 | 实际持物开度 |
| U→D | 附着，允许正确的终端罐子—桌面支撑 | 持物 |
| D→U | 罐子留在 D，成为静态障碍 | 打开 |
| U→N | 罐子继续留在 world | 打开 |

所有机器人 link 始终检查桌面与其他障碍。

允许罐子建立支撑，不等于允许手指穿桌面；也不能让附着罐子跟着空手回到 neutral。

## B2. 先运行当前唯一内移布局

验证：

```text
C / U_new / D_new 的完整约束 IK
→ U_new / D_new / U_new / N 的路径
```

新布局保留现有 10 cm 内移方案，不先扩大位置搜索。

使用已经验证的 reported/actual/solver 坐标转换、实际夹爪状态和碰撞世界。endpoint 与路线成功分开记录。

## B3. 通过后直接完成新场景的完整 root

不再等待单独的 root 审批：

```text
新布局
→ 新 current/anchor
→ 新场景下真实公共抓取前缀
→ inside/on/beside 三分支资格与规划
→ 三分支实际执行
→ 独立验收与原子发布
```

inside 必须是：

```text
受控进入
→ 正确支撑
→ 慢释放
→ settle
→ strict-inside
```

不能回退空中松爪掉落。

旧 inside 5/5 只能作为历史正证据；新布局仍要完成本身的规划和物理验证。

## B4. 当前布局失败时，允许证据驱动修订，不要求守住最早的坐标

在本 Goal 范围内，可以提交并执行最多三个版本化布局/抓取实现修订，条件是：

- 保留三种关系意图与互斥 verifier；
- 同一个 root 的三个分支仍共享 current；
- 每个新版本先冻结目标、生成方式和候选顺序；
- 不根据成功结果事后改版本身份；
- 使用已知可达范围和几何约束推导，而非大规模随机位置扫描。

不允许为了让 F2 “完成”，删除 inside、换成三个简单方向移动，或改写标签含义。

F2-A 通过后，继续生成 B 根及 path/motion，补齐 F2 的十二个 pilot 格子。

---

# 7. 工作线 C：完成 F4-B，不让低估预算成为永久阻塞

目前 F4-B 的直接入口要求新布局对应的资格终端，因此原 `14 scenes / 136 queries` 不足；已审计的下界至少是 `17 scenes / 262 queries`，还可能有额外前置成本。fileciteturn485file0L2-L2

**本 Goal 允许在总预算内自行生成正确子预算，不再为 136→262 这类真实调用量差异单独停下来等审批。**

执行原则：

1. 先把全部必需资格、template、prefix、root、motion 的实际调用链算完整。
2. 保留当前工作过的入口。
3. 不通过删除资格检查或冒用 A 的回执来压低预算。
4. 若安全复用同一状态下的规划能减少重复，必须先证明状态、模型、source 和 controls 一致；不要为节省少量查询优先重写整个框架。
5. 采用真正的新 B root，生成自己的 current、anchor、prefix 和 controls。
6. 先验收三个 `r_pc`，再使用 B 自己的 controls 执行三个 motion 变体。
7. 采用已验证的 UTF-8 原子发布与 finalized receipt 顺序。

A/B 的相关场景 lineage 保留，不把 10 mm 布局变动描述成强泛化测试。

完成 F4-B 后，F4 的十二个 pilot 输入格应齐备。已完成的 F4-A 不再重采。

---

# 8. 公共采集链：一次集成好，不再不断新建 wrapper

## 8.1 固定生产入口

每个 family 可以保留不同的已验证 source profile，但应共享稳定的任务生命周期：

```text
读取任务与预算
→ source/asset/model 校验
→ GPU lease
→ 场景创建
→ current/anchor/trace 初始化
→ 规划与执行
→ 原始证据保存
→ family verifier
→ finalized receipts
→ raw/video 独立复验
→ root/cohort 验收
→ publication index
→ cleanup
```

对这一整条入口做测试，不能只测试内层函数。

当前 F3 新入口已经把 trace 初始化、primary/secondary error 和计数放在实际 `run()` 中，应继续沿用这个方向。fileciteturn486file0L2-L2

## 8.2 失败恢复不再逐项外审

普通接线错误发生后：

```text
保存原失败
→ 定位根因
→ 增加能复现问题的实际入口测试
→ 修复
→ 新版本/新 attempt
→ 在总预算内继续
```

原尝试仍计入消耗。不能把已创建场景但尚未动作，统统写成“零消费”。

相同错误再次发生时，应检查共享入口或依赖，不再只给单个脚本贴同样补丁。

## 8.3 已完整采到数据、仅元数据出错时

允许做追加式 CPU 更正，但仅限：

- 原 raw、trace、视频完整；
- 更正值能够从原始证据独立重算；
- 不改变动作、标签、物理结果或成功阈值；
- 保留原失败终端与原文件；
- 新的 resolution 和 acceptance 独立发布；
- 重复审计不重复入账。

缺失的物理事实不能由 CPU 推测补造。需要放宽科学标准才能采纳时，必须停止并报告。

---

# 9. 完成 48 格并做独立验收

## 9.1 复用已有 18 格

只读核对：

```text
F1-A 六格
F1-B 六格
F4-A 六格
```

通过后，在本 Goal 的 pilot 输入授权下显式登记。保留原 development 来源与任何合法 resolution，不把它们伪装成新采数据。

## 9.2 补其余格子

```text
F2-A/B：12
F3-A/B：12
F4-B：6
```

每个 cell 都有唯一 rollout ID、raw 身份和对应 source/spec。

不能跨 root 填格，不能用一条 raw 填两个 realization。

## 9.3 不只检查“文件存在”

独立验收脚本直接读取磁盘并核对：

```text
raw / manifest / sidecar / trace / MP4
N actions 与 N+1 states 的时间关系
current 从真实初始状态读取
程序、对象、关系与实现类型
同根 current/anchor
该 cohort 的 prefix/event 对齐
F3/F4 的顺序与终态
实际路径/时长变化
失败历史与所有资源计数
```

路径、文件名、branch ID、planner ID 不得进入模型输入。

涉及同意图不同实现时，不要要求所有自由路径前缀都逐字相同；严格前缀 cohort 与自由 realization cohort 必须按主协议区分。

## 9.4 将科学负例保留为负例

错误程序、错误对象、非法 shuffle、缺少关键事件的数据不能通过 verifier。

CPU 合成负例必须标为测试 fixture，不得写入成功 rollout 数据集。

任何数据规则缺陷，先做回归与影响清单；不能只让当前样本过关。

---

# 10. 做一次连续采集检查，证明不是“修一条、采一条”

在剩余 pilot cells 中，预先安排一段：

```text
至少连续六条真实采集
覆盖至少两个 family
使用同一冻结版本集合
中途不修改源码、目标规则或 verifier
```

这不是新增六条额外配额，优先从尚未采的 pilot cells 中安排。

检查：

- 是否无需人工修补；
- 成功与失败是否都能自动封存；
- 是否完整清理并继续下一项；
- 实际每条、每根 query/scene/用时；
- 任务队列是否能从 checkpoint 正确恢复。

若中途必须改代码，先修复，再用下一段预注册任务验证。已经成功的数据不为凑“连续成功”重复采集。

**六条连续成功也不证明正式生产成功率已经足够高。**它只用于确认接口能连续工作；生产可靠性仍报告实际分母，不编造“90% 已完成”之类数字。

---

# 11. 持续执行、检查点和停点规则

## 11.1 不应停止的情况

以下情况不构成返回用户的理由：

```text
完成了一份 proposal
通过了 CPU tests
某个 helper 已接好
F3 micro 成功但 shared-V 还没做
F2 endpoint 成功但 root 还没做
一个 family 成功，其他还有可做任务
需要在总预算内签发新的范围内子作业
普通实现缺陷可以自行修复
```

应更新 checkpoint，继续下一项。

## 11.2 应暂停对应工作线的情况

```text
同类问题三个有依据的修订仍未解决
需要改变 family 科学定义
需要放宽既定物理/verifier 阈值
原始证据不足以判断成功
本族继续运行可能消耗其他族完成所需的全部余量
```

暂停该工作线后，继续其他独立 family 和 CPU 验收。全部可做任务都推进完后，统一汇报，不要因为一个 family 卡住就让整个 Goal闲置。

## 11.3 必须暂停 GPU 队列的情况

```text
累计预算达到上限
资源消耗无法核清
GPU UUID/lease 不一致
本任务残留进程无法清理
共享驱动或管理员权限问题
数据污染、hash 不一致且原因未明
用户明确暂停
```

不得杀其他人的进程、重启服务器、重装共享驱动或降低 Guard 来继续运行。

所有 GPU 忙时释放等待资源，继续 CPU 工作或进入可恢复等待；不能忙循环反复重启 Goal。

## 11.4 检查点文件保持精简

维护：

```text
GOAL.md
STATE.json
budget_ledger.jsonl
attempts.jsonl
pilot_cells.json
FINAL_REPORT.md
```

文件名可与现有结构合并，不要求另造一个框架。

`STATE.json` 至少记录：

```text
当前 source profiles
各 family 当前阶段
已完成及失败尝试
总预算消耗/预留/剩余
正在运行的 PID/PGID/lease
下一个可执行任务
真正阻塞原因
```

压缩上下文、重启会话或中断后，先读取 checkpoint 和实际进程状态，不能重复启动同一作业。

若环境支持子代理，可分配 CPU 代码审阅、独立验收和预算核对；**仅一个主调度者拥有 GPU 启动和总账写入职责**。不要让多个代理分别创建独立预算。

---

# 12. 最终交付与状态判定

成功结束时交付：

1. 四族真实采集能力的证据索引。
2. 八个 pilot 根、48 格输入数据与逐格验收结果。
3. 可复现的 collector 入口、source profiles、环境和资产锁定。
4. 完整失败分母、预算消耗、每根实际成本。
5. 连续采集检查结果。
6. 正式 360 条的协议、生成器、split、reserve 和总预算草案。
7. 哪些机制实验仍未执行的明确清单。

最终状态分开写：

```text
FOUR_FAMILY_COLLECTION_PASS
PILOT_INPUT_48_OF_48_ACCEPTED
COLLECTOR_CONTINUOUS_RUN_VERIFIED
FORMAL_PROTOCOL_DRAFT_READY
```

只有满足各自证据时才标为 true。

以下状态本 Goal 结束时仍保持关闭：

```text
formal_360_execution_authorized = false
model_training_authorized = false
pi05_training_started = false
H_reveal_measured = false
compression_validated = false
```

若目标未全部达成，输出：

```text
已完成到哪个阶段
剩余的最小障碍
已经排除的错误方向
真实预算消耗
继续需要的唯一关键决策
```

不得仅写“等 GPT 再看看”，也不得把资源暂停标成技术成功。

---

## 最后给你的建议

这份任务最关键的不是更长，而是**真正允许 Codex 从 micro 一路推进到 shared-V、root、realization 和 48 格验收，同时允许有依据的修复与重试**。

以前的规则常常是：

```text
做到下一步之前 → 再回来审批
```

这次改成：

```text
总目标和底线一次说清
→ 范围内自行实现、验证、修复、继续
→ 达标或碰到真正边界才停
```

**它能减少反复交接，但不能保证所有物理问题必定在给定预算内解决。**因此终点必须是“真实四族贯通与数据验收”，而不是让 Codex为了结束 Goal，把最后几个失败条件改成通过。

---

If you want, I can:

- 继续详细描述工作线D的具体任务
- 解释F3工作线失败处理流程具体操作
- 列出用以验证四族数据完整性的具体验收标准
