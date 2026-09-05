# F2 几何来源澄清 + F3 pre-close micro runtime 窄复审

依据用户转交的最新外审 `https://chatgpt.com/s/t_6a9b97991a788191939fe2d8b6dec5d9` 继续实施。完整原文已保存为 `EXTERNAL_REVIEW_F4_ROOT_F2_BESIDE_F3_WIRING_20260905.md`，SHA-256=`7326b7321b02182c6ba803d3c8e379654301aaadb82dd45229c406c4d28fb45b`；正文完整 16,355 字符，未发现额外附件下载链接。

本请求只审两件事，不重新审议 F1–F4 科学定义，也不申请 Stage 1、formal 360、训练、H-reveal、compression 或 π0.5。F4 V2.2 唯一 root 已按独立批准执行，其最终结论以本次另外发布的 terminal publication 和统一 readiness 为准，不作为 F2/F3 的授权。

## 1. F2：语义修复已实现，但外审数字与 live 几何来源不一致

Run3 的 inside 5/5 planner receipt 保持字节不变；没有重跑 inside、完整 11-query 或启动任何新 F2 GPU/scene/physical attempt。beside-only 的条件许可没有被当作更换几何来源的许可。

已实现 `f2_beside_only_completion_runtime_v1/semantic_target.py`：从 candidate 2 的 geometry-centre XY、原 orientation、support plane、local centre 和 half extents 重算 actor origin；用 candidate 0 的历史 actor pose 整体平移到 candidate 2 独立复核。保持原 six-segment 顺序、neutral、seed、asset、arm、target-binding 容差和 annulus 不变。`scene_attempt.py` 在 derivation 异常时也保存 planner before/after、scene instance、cleanup 和 error。

9/9 CPU 回归通过，具体测试输出与源码哈希保存在 `F2_F3_CPU_IMPLEMENTATION_REVIEW_20260905_V1.json`。这不是 F2 physical pass，也不是完整 beside runner 已可上线。

### 必须澄清的来源差异

| 项目 | 外审引用的 collision inventory | 当前 live helper 使用的 model_data |
| --- | --- | --- |
| local centre x (m) | -2.9668211936947214e-6 | -1.079751295975455e-5 |
| local centre y (m) | 0.04776370921172202 | 0.047754681682482036 |
| local centre z (m) | -3.6194920539859426e-6 | +9.404121786554337e-6 |
| actor-origin XY 补偿 (µm) | (+3.619492, +2.966821) | (-9.404122, +10.797513) |

来源一是 `F2_GEOMETRY_CERTIFICATE_INVENTORY_V4.json` 的 collision geometry；来源二是 `family_runners_v3_1.py::_actor_local_geometry_bounds` 读取 actor.config 的 model_data centre/extents，再乘 scale=0.05。没有发现该 can 的 `_cmf_` geometry override。

当前 `assets/objects/071_can/model_data0.json` SHA=`78eb137b42da2d6fa0b9208717964838e01cf6c65c5c6b14ad7c988d6ff2acfb`。metadata 半尺寸为 `[0.035574561110057905, 0.04823394409127801, 0.03559387691939824]` m。

使用现有 live 来源重算得到：

```text
candidate geometry XY = [0.08000000000000002, 0.07]
support plane = 0.74 m
orientation wxyz = [0.5, 0.5, 0.5, 0.5]
actor pose = [0.07999059587821346, 0.07001079751295976,
              0.7404792624087959, 0.5, 0.5, 0.5, 0.5]
composed geometry-centre XY = [0.08000000000000002, 0.07]
old overwrite error = 14.318651916 µm
```

这与历史 candidate 0 actor pose 加 `candidate2_xy - candidate0_xy` 完全一致；不是放宽容差得到的通过。完整六目标、变换和哈希在 `F2_BESIDE_GEOMETRY_SOURCE_DISCREPANCY_20260905.json`，receipt=`cd2eca9e5feb564d6b21ccb9f54d77cdb74d910c07204199da2b77449fadd6eb`。

请只明确：是否修正上一外审的约 3.619492/2.966821 µm 数值要求，允许保留现有 live metadata 几何来源，并据此完成原条件许可中的 **beside-only 6 queries / 1 fresh scene / 0 physical / 0 raw / 0 root**？建议保留 live 来源；若要求切换 collision bounds，应单独审计其对 pose、support height、既有 certificate/targets 的影响，不冒充只修 XY。

来源明确后，仍需完成 beside-only 专属 runner/Guard/manifest、真实 CPU preflight 和 source publication；不能直接用这份 CPU 函数或旧完整 Gate 上 GPU。成功时只将保留的 inside 5/5 与新 beside 6/6 合成 route qualification 11/11，再准备 controlled-insertion root V2 proposal；不自动执行 root。

## 2. F3：精确候选冻结与真实执行调用链已经接线，申请窄复审

冻结文件：`F3_DETERMINISTIC_CANDIDATE_FREEZE_RESOLVED_V1.json`。四完整 recipe 和 SHA 原样保留：

| 顺序 | recipe | SHA-256 |
| --- | --- | --- |
| 1 | r3063 / bottle13 / left | e612c0a829559966bae718bd3a995fe4d87b731de2680c38a56f325cedf2fb79 |
| 2 | r0861 / bottle15 / right | 546859c30a0d068f1ca8103e5def09a450a84016980d766d479949d908ceadbd |
| 3 | r1401 / bottle5 / left | 599934ea0592589f4daa7b9daffc72c42a5a527ce2bd50911fd3b85a80ee883d |
| 4 | r2526 / bottle4 / right | 2b9c30ea466d6350b04add4102eda9aa004f22f9589224284ed5851dd681b5ae |

Universe SHA=`4bc99d0957dcd2dd955e6060cbe2a077cec1a2cd71ef7eecf1eca9375b16de46`；执行事实源是最新外审给出的 exact recipe IDs/hashes，不再依赖缺少 payload 的旧 rule hash。文件中的 `decision_receipt_sha256` 只保留上一份 CPU 冻结决定的父 lineage，`authority_source` 指向本次 exact recipe 决定；两者均不是 GPU execution approval。

新增文件：

- `f3_preclose_candidate_micro_runtime_v1/manifest_contract.py`
- `f3_preclose_candidate_micro_runtime_v1/guarded_launcher.py`
- `f3_preclose_candidate_micro_runtime_v1/job_runner.py`
- `f3_preclose_candidate_micro_runtime_v1/candidate_executor.py`
- `f3_preclose_candidate_micro_runtime_v1/test_executor.py`
- `PROPOSED_F3_PRECLOSE_CANDIDATE_MICRO_MANIFEST_V1.json`

真实调用链为 Guard → runner → `run_candidate`，不调用旧的立即闭爪 `execute_f3_level2_physical_v1`。先按固定次序 Stage A 3-query / Stage B 7-query qualification；通过者再按固定次序在 fresh scene 进行 3-query micro。pregrasp 完整窗口 Gate 失败不执行 grasp；grasp 完整窗口 Gate 失败不 close；通过后才 close 0.50 → hold 250 → frozen 25 mm lift → contact continuity/off-support/relative-transform 检查 → stop。达到两次 physical pass 立即停止，没有 shared-V、suffix、raw trajectory 或 root。

Gate 仍是原 `f3_preclose_physical_consistency_gate_v1_1/gate.py`，没有新阈值或 V1.2。窗口为每段 `start+1..end` 所有实际 trace rows，端点 qpos/EEF 加全窗 contact/displacement。micro 后 contact continuity 覆盖 lift 窗口，off-support 检查 lift 末端，relative transform 使用既有 5 mm / 0.05 rad 界限；这些是待审 runtime 细节，尚未获得真实 physical 正证据。

预算上限仍为 qualification 40 queries / 8 scenes，micro 12 queries / 4 scenes / 4 attempts，合计 52 queries / 12 scenes；四旧候选排除，不在线搜索、不 fallback、不 seed retry、不成功条件替换。physical planner seed=20260829；Stage A/B reset nonce 的确定性规则在新源码中冻结，不宣称 bitwise planner determinism。

异常闭包：setup/target/execute/trace/cleanup 的异常均生成 scene-attempt receipt；进入 scene 后缺失末端 counter 保留 unknown，不伪装成零；scene receipt 绑定 recipe、scene instance、scene-binding equivalence、查询 delta 与 cleanup。按阶段和每场景核算预算。新 Guard 从 F4 V2.2 适配，持有 flock 直到 13×5s cooldown 完成；runner 验证 parent/start receipt/UUID/lease，结束后核对 terminal 计数与科学失败退出码。所有输出采用新 namespace，不覆盖旧 artifacts。

### 已执行的 CPU 验证与限制

- 新 executor/accounting/terminal/Guard tests：23/23。
- 未修改的 full-window Gate tests：8/8；此前四条 sealed trace 的完整回放仍以 `F3_FULL_WINDOW_REPLAY_V1_1_20260905.json` 为依据，本次没有伪造新 physical trace。
- 真实 proposal Guard → runner CPU preflight 通过，且重建四条实际 Stage-A bound specs；没有 scene、planner、CUDA、lease 或 output namespace。
- F3 proposal output/Guard/cache-job 在 CPU 检查前后都 absent；approved/GPU/all later gates=false。
- CPU receipt=`566ee8ec93cd3ee1957a1ac44d1342b4cf217b34a1056495155d9e35527d52d4`，包含完整命令、23/8/9 tests 输出与当前 source hashes。

以上单元测试使用 CPU / mocks，不等同于新 Guard 的真实 GPU 生命周期验证，更不等同于四个新候选抓取成功。请重点审计真实 executor 顺序、trace 字段映射、contact/off-support/transform 范围、52/12/4 accounting、实际 source/decision binding 和失败闭包。发现问题请给最小修正，不扩大候选或预算。

如批准，请给单独结构化决定 `F3_PRECLOSE_CANDIDATE_MICRO_EXECUTION_V1`，绑定最终 proposal 中的 `candidate_freeze_sha256`、`caps`、`source_files`，明确 `authorized=true`；不能仅凭本文或旧候选冻结许可执行。后续才生成唯一 approved manifest，CPU preflight/push/fresh GPU Guard 后执行一次。GPU 仍只用实时 fresh-idle 的物理 0–7，按最新外审队列串行，不与 F4/F2 同时运行。

## 3. F1 与整体边界

F1 仍为 5 个 development r_pc roots / 15 trajectories；`F1_REALIZATION_DESIGN_CPU_20260905.md` 只补充 r_inv_path/r_inv_motion 的真实独立 rollout、配对 receipt、anchor/event 对齐和 root 3×3 原子验收设计，没有收集或 promotion。

Stage 0 已封存且未重跑。Stage 1 仍未授权、formal 仍 0/360，训练、H-reveal、compression 和 π0.5 继续禁止。F4 新结果只增加 verified development evidence，不自动增加这些阶段的分母。
