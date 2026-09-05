# 9-realization 首入口失败与精确恢复路线

## 当前结论

本轮已真实启动，不是仍停在计划。新批次首 F1-A cell 在 same-current 重建检查失败，整批按规定停止：1 个 fresh scene、0 个 planner query、0 个物理动作 rollout、0 个新增 raw；剩余 8 格未运行。GPU2 已完整释放。已有开发数据仍为 F1 5 roots/15 trajectories + F4 1 root/3 trajectories，Stage1=0/48、formal=0/360。

源码和清单先发布于 Vault `91c11fc`。本次 V1 代码、清单、失败 dataset、Guard 和回执均不可覆盖或再次启动。Stage0/F4 原采纳记录保持不变。

## 失败原因及本轮遗漏

F1-A/B 原 reference 的 `simulation_configuration.implementation_source_sha256` 是 `9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72`；新批次使用当前 `3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7`。这个全源码指纹进入 reconstruction hash，故旧 reference 不能直接与当前 adapter 产生的 reconstruction 比较通过。F4 原 reference 已是当前版本，没有这个已知冲突。

错误原文：`fresh reconstruction failed same-current reconstruction_spec_aggregate_sha256`。这不是目标规划/抓取失败，也没有证据说 GPU 驱动坏了。

12 项 CPU 集成测试确实通过了原 family verifier、raw writer/loader、retiming、suffix 落盘、分段 trace 对齐和两阶段 publication，但漏测了旧 reference 与新 runtime 指纹兼容性。因此先前“执行前检查完成”不够充分，这一遗漏属于执行器接线责任。新增 CPU source-lineage preflight 用 9 个断言正确提前拒绝两个 F1 cohort；不能继续用旧 12 项通过来证明入口安全。

另一个证据接线遗漏：V1 保存了异常文本，却没有保存异常携带的详细 mismatch receipt 或 candidate current。不能事后编造 live candidate hashes。只修改 source 字段即可复现相同报错，是明确标注的 CPU 反例，不是新现场证据。

## 已完成的源码追溯

- Vault `317387b` 的 `代码审阅快照/controlled_multi_future/` 含 245 个 Python 文件。逐文件按运行时规则重算整树指纹，精确得到旧 `9873bbe…`，历史源码未丢失。
- F1 batch adapter、v1_2/v1_3/v1_5 adapter、runtime_trace 和 canonical_prefix_replay 与当前版本逐字节相同。
- F1ControllerV3_3、执行 cached segment 和缓存预规划控制等顶层 AST 未变；共享 frozen suffix writer/validator、raw writer 和 canonical hash 实现有后续变化。因此不能直接声明整个新 runtime 与旧 runtime 完全等价，更不能静默替换历史 source hash。

## 修复路线：先 CPU，后明确恢复范围

1. 首选建立独立的旧 F1 source bundle，完整保持 `9873bbe…` 245-file 树，不回退 active `3ec56ec…`。将资产/config 路径显式绑定到已核验的工作区路径，不引入旧服务器路径。
2. 在 bundle 外适配新 realization collector 与既有 Guard；F1 使用原源，F4 使用当前源，分开进程命名空间，避免同一 `controlled_multi_future` import cache 混用两个版本。渲染继续 UUID/PCI 绑定，不能回到未绑定 renderer。
3. CPU 必测：实际导入来源及全树 hash、原 current/reconstruction/anchor 元数据口径、source mismatch 在 scene 前拒绝、原控制与新 retiming 的实际磁盘 loader、family verifier、两阶段发布、失败 finally live 计数、candidate current/mismatch receipt 在 require_same_current 前后都能保留。
4. 如果旧 F1 bundle 与新桥接不可直接兼容，应提交明确的 source-compatibility impact review；不得删除源码字段、放宽原 same-current Gate、重写旧 reference/anchor 或假称 live source 仍为旧 hash。
5. 完成以上 CPU 工作后，再签发精确恢复范围：首个零动作基础设施失败 cell 是否可 replacement，以及剩余 8 个未尝试 cell 的恢复。原场景 1 已消费；若重新完成 9 个新 scene，累计应明记为 10，而不是继续报告总共 9。原 query 消费为 0，计划新查询仍 123（F1-A33、F1-B0、F4-A90），不得用“零动作”抹掉已消费 scene/attempt。

本轮没有创建恢复执行许可、没有重试，没有接受 source overlay。CPU 修复可继续自主推进；新的 GPU 恢复必须符合上一决定的 global-stop/no-auto-retry 限制。

## 审计入口

### 后续CPU修复已落实（本轮追加）

已创建独立 sparse worktree `/nfs_share/lijunhui/Robotwin2/tmp/cmf_f1_parent_317387b`，旧245-file源码逐字节保留且tracked clean；非active源码回退。`realization_parent_f1_bridge_cpu_v1.py`以独立模块命名空间加载原adapter，显式重定位资产根到现有工作区，并逐一验证旧asset/config/critical-source锁。六个F1格的原suffix loader/verifier和CPU配置hash兼容性检查通过。

`realization_batch_runtime_v1_1/`已接入这个adapter桥接，新增在比较前落盘candidate current、异常时保留完整mismatch receipt；修正桥接不应抢占其他runtime import搜索路径的问题。15项CPU测试通过，包含三个cohort的source binding及模块分派来源检查。V1原目录/清单保持不变；V1.1执行入口明确拒绝复用旧授权，尚无新execution manifest或GPU-ready声明。需要确认恢复范围后，完成对应新manifest/Guard分派预检，再做live验证。

因此上文修复路线1已完成、路线2/3的CPU接线与15tests已完成；后续仍须新恢复许可的准确接线和实际scene/anchor验收。没有因为CPU恢复成功就记新增数据或宣布整个问题已经物理修好。

- `REALIZATION_BATCH_TERMINAL_PUBLICATION_V1_20260905.json`：job、Guard、POST_CHILD、首 cell 和全部原产物文件 hash。
- `REALIZATION_RECOVERY_CPU_REVIEW_V1_1_20260905.json`：CPU修复源码hash、15tests、旧source bundle与精确恢复提案。
- `STAGE1_READINESS_AFTER_REALIZATION_SOURCE_MISMATCH_20260905.{json,md}`：最新统一状态。
- `REALIZATION_PARENT_SOURCE_COMPATIBILITY_CPU_AUDIT_V1_20260905.json` 与 `realization_source_compatibility_cpu_v1.py`：可重跑的 CPU-only 阻断检查，无验收覆盖层。
- `REALIZATION_BATCH_APPROVED_MANIFEST_V1_20260905.json`：已消费/停止的原 V1 清单，不可重发。
- 日志 §470–§473：完整许可、CPU 失败及修正、真实启动与释放、根因和证据限制。

F2 endpoint constraint decomposition 和 F3 world/gripper model repair 尚未新增运行；本次完整性 global-stop 后，不绕到另一族启动 GPU。Stage1、formal360、training、H-reveal、compression、π0.5仍禁止。
