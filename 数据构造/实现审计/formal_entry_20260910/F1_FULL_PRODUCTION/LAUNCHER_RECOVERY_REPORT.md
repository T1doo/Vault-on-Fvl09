# F1 launcher 有界恢复、CPU副本恢复与异常计量

本轮修改只在现有 `first_wave_launcher.py`、`execution_cli.py` 和对应测试内；继续使用原 `ExecutionLedgerV2`、GPU Guard、物理index/UUID lease和原生F1入口。未执行真实GPU快照、规划、物理采集或训练，测试使用明确CPU host/simulator边界。

## 可调用接口

```python
launch_wave(manifest, state_dir, backend=None,
    ready_job_ids=None, recovery_requests=None,
    copy_only_job_ids=None, activated_jobs=None,
    compatibility_ref=None)
reconcile_saved_attempts(manifest, state_dir, job_ids=None)
validate_compatibility(manifest, state_dir, reference, activated_jobs=None)
verify_completed_job(job, allow_synthetic=False)
```

`scope=F1_FULL_PRODUCTION`允许冻结全族jobs的ready子集，旧两root默认调用兼容。额外reserve job必须带 `activation_receipt={path,sha256}`；核对原plan hash、预注册reserve、失败primary lineage、继承split/difficulty、实际resolved科学字段和正式verifier合同。job选择不改变manifest或账本合同hash。

每root首次child绑定GPU UUID，恢复只使用该卡；忙卡不以其他卡继续拼同root。并发复用旧分配函数，整体受 `max_concurrent_gpu_jobs` 限制，CPU copy受 `max_copy_workers` semaphore限制。

## 有界恢复

- 首次启动拒绝非空输出；恢复必须有明确request ID、failure class和mode。
- 已知GPU执行次数由实际child启动计数，最多配置的两次；逐次证据另有独立attempt编号。
- `DEFERRED_READY`是无child的lease竞争或fresh-idle阻断，不消费GPU执行次数；已取得lease的真实时间照计，物理计数为零。
- 每attempt预留取单次模板与root累计剩余额度的较小值，所有attempt仍用同一全族ledger。
- usage从历史原件累计读取，再减该attempt开头已结算baseline；不能把恢复后全部历史又记一遍。
- request ID幂等；旧成功raw、manifest、capture和anchor实际文件hash在恢复前与恢复后核对。
- latest cohort pointer决定当前失败分类，旧失败不会覆盖新失败；旧独立pass报告必须与当前完成checkpoint/spec相符，不能误分类为copy-only。

自动有限恢复的已知类型：planner/任务可行性失败为`physical_infeasible`，实际执行失败为`transient_execution`。`failed_independent_cell`只有独立gate明确给出`PHYSICAL_FAILURE`才归入物理失败；缺图、缺字段、错误阶段、未知错误、prefix/candidate/cleanup等问题保守停止。共享接口错误必须先有实际修复证据，不能仅改标签放行。

## copy-only

GPU child运行 `execution_cli --collect-only`，收集及独立验收完成后先保存结束/清理/释放证据并结算物理消耗，随后CPU调用copy。copy失败输出`COPY_FAILED`和`root_collection_verified=True`。

`copy_only_job_ids`路径不构造HostBackend、不请求snapshot/lease、不调用原生场景。先检查已结算和owned cleanup/release；再只读重算F1原始数据、cell/root语义与模型出口。原 `independent_structure.json` 不覆盖；新增内容寻址的`copy_revalidations/`原件。原始成功数据仍按原回执复制，恢复记录关联本次重验。

重复copy恢复仍重新核对独立root、整包`portable.read_root`、group/common、跨anchor等价、registry和九格身份，不只相信旧PASS。

## 异常计量与协调者恢复

acquire返回后立即保存job/attempt、物理index/UUID、host、PID、wall/monotonic时钟身份与起点；在snapshot或child之前完成持久化。每条路径分别保存child terminal、owned cleanup、lease release确认或未确认状态、实测终点/时长。

`lease_terminal.json`优先独立写入，release日志写失败不阻止已测区间保存；额外写入持久化错误和测量备份。HostBackend的child日志写失败不跳过finally里的owned terminate/reap。已知 `launched=False` 不计child次数；backend异常且缺清理证明时绝不因没有process_start文件猜测无child。

可靠host进程树已证明owned cleanup时，post snapshot失败不抹掉实测时间：明确保留post error，device idle未知，允许安全释放并结算已知消耗。清理或释放未证实则结束时间/lease秒保持未知，reservation保留。

`reconcile_saved_attempts`只使用原先保存的可靠terminal/usage证据，按同一幂等settlement恢复；不拿重启时的当前时间补造旧lease终点。RUNNING/UNRESOLVED可能恢复；缺原始结束/清理/释放证据保持未知，不能把全部预留当实耗。已采齐但settle失败的root恢复后进入copy-only，不重采。

## 明确源码兼容附录

原manifest和账本hash不变。新源码必须有独立 `f1_runtime_compatibility_appendix_v1`，绑定原manifest、旧/新source bundle、完整changed_files、每个文件的科学合同影响说明、适用replacement job字节hash。

每个root另有hash绑定的`f1_source_compatibility_v1`：相同科学spec、旧/新native implementation hash、旧/新完整source bundle、实际已通过cell的raw/manifest/capture hash。运行时在新实现下真实CPU重验这些cell；不是仅信旧pass字段。budget、output、scene/program/阈值等科学spec不得通过source-only附录改变。

已修共享失败另须`failure_resolution`，明确原failure class、`FIXED_CPU_VERIFIED`及hash绑定的新源码回归证据。未列入适用范围的jobs继续阻断。SOURCE_CHANGED只在有此证明、没有未知reservation/overrun时解除，并追加原错误与修订记录。

当前支持有限一次source-only转换；后续多代改动需要新的累计影响附录。改变物理/观测/实际prefix或suffix控制的修复仍会被原生严格重放核对拒绝；不自动判全部旧数据失效，也不伪造兼容或修改旧raw。

## 针对性验证

最后冻结轮：原launcher9项及新增恢复/异常16项共25项通过；另外3个完整真实函数调用链测试通过。新增测试覆盖：

- 部分成功后真实launcher/CLI恢复缺格，原red只执行一次，raw字节不变；重复request不新增snapshot。
- 真实九格保存/独立验收后注入copy失败，释放及结算已完成；CPU-only恢复九包，原raw及accepted root报告不变。
- 未附证明的源码版本变化在GPU前拒绝；附明确source-only审查、实际旧cell重验后恢复成功，账本合同hash保持原值。
- acquire后持久化失败、child退出usage解析失败、post snapshot失败、settle失败、release未证实、backend异常无cleanup、协调者重启幂等结算。
- 子进程结束日志失败仍terminate/reap；release日志失败仍保留实测terminal。
- 无child busy、prelease拒绝、latest失败分类、实际terminal枚举和原成功数据保护。

异常与Guard单元测试的host、计量回执是synthetic；真正的launcher、ledger、状态、配置hash和恢复代码运行。三个整链测试仅替换simulator adapter，capture/raw保存、独立验收、export和copy实际执行。所有fixture明确synthetic/research-ineligible，不计入正式90条。

命令（项目env，CPU）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest test_launcher_recovery test_first_wave_launcher -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest test_launcher_real_pipeline -v
```

新场景物理可行性、真实GPU driver/renderer、宿主机worker清理与实际耗时仍由未来获批Luna任务实测。本报告不授予GPU或formal执行许可。

## 调用链紧上界与管理cap分开

现管理cap不修改，但它不是“必需支出”或预测成本。按本版最多两个实际GPU child/root、首个未接受cell即停止、已完成cohort跳过、通过cell复用、branch只执行frozen controls且无额外planner的条件：

- 正常成功九格：33 fresh / 21 action / 9 collection / 192 solver上限。
- 最坏第一次在最后cohort最后cell失败，第二次完成或再次失败：正常基数再加8 fresh资格/preflight +1失败collection；action加4+1，solver加64。紧上界为42 / 26 / 10 / 256。
- 66 / 42 / 18 / 384是更宽的每root管理包络，来源于“每cohort都可重做一次”的保守预留；当前root最多2 child时，不应把这层包络描述为实际必需开销。
- 最多14个实际执行root的上述物理紧界为588 / 364 / 140 / 3584，低于冻结管理cap924 / 588 / 252 / 5376。失败root成本不因reserve替换消失。
- GPU201600秒仍是28个有界child lease的保守总包络，不是实测耗时预测；无child busy仅增加实际lease时间，不增加上述四项物理计数。

这些紧界依赖前述fail-stop/复用条件。如果实际调用链额外执行任务或已知消耗越界，仍必须照实记账和执行overrun规则，不能用数学包络覆盖实际原件。
