# 正式批量入口与预开批检查

本轮已实现独立版本代码，状态为 **CPU_RUNTIME_READY / FIRST_WAVE_PHYSICS_PENDING**。不是第二份纯计划，也没有开始正式采集。

- `scene_plan.py`：具体四族场景、资产绑定、完整program步骤、投影难度、任务几何近重复、56slot及确定性reserve。
- `execution_cli.py`：通用root九格实际family调用，独立验收后自动封存及副本；首波`first_wave_launcher.py`复用Guard与ledger，显式预算/源码/配置绑定。
- `native_f1*`、`native_f2f3.py/native_cells.py/native_scenes.py`、`native_f4*`：保留成功控制方案的新接口；旧源码、旧P4与原raw未覆盖。
- `portable_v2.py/formal_export.py/f1_portable_export.py`：来源索引预期hash→原件→副本，严格读取、原子root发布、版本冲突拒绝与复制恢复。
- `INDEPENDENT_REVIEW.md`：独立反例和修复。F1/F4采用模拟器adapter边界fixture；F2/F3替换物理cell engine，真实root状态/磁盘验收/复制函数运行；不冒称测试原生控制动力学。
- 四族各一条真实迁移样本见`FINAL_READER_REAL_SAMPLES.json`。最终reader也已复制到各包的versioned addon，并在禁止原datasets/project/Vault访问下全部读回。旧bundle/原raw不变；总复制仍低于2GB。

执行前从`EXECUTION_HANDOFF.md`开始。`F1_FIRST_WAVE`恰好两个新F1 root、18条目标；包含恢复的上限为fresh132/action84/collection36/solver768/GPU14400s，全部授权标志仍false。`FIRST_WAVE_GATE_CHECK.json`证明其在GPU快照前拒绝执行。

新场景真实可行性、首波成本与RSS、350GiB个人配额、逐族Stage2→Stage3调度解释仍待执行前确认/实测。formal360、模型、H-reveal、压缩与HD均未启动；P4采集完成不变。

运行源锁在`SOURCE_FREEZE.json`；新源码直接纳入Vault，既有实际运行依赖原字节封存在`RUNTIME_DEPENDENCIES.tar.gz`（按LIVE相对路径，不含raw/凭据/环境）。`DELIVERY_MANIFEST.json`绑定审阅材料。数据副本在`/nfs_share/lijunhui/CVPR_FutureIntent_Data/formal_entry_20260910_samples/`，不入Git，同NFS不称异地备份。
