# 正式入口实现交接（CPU已检查，首波待批准）

本轮依据审阅`t_6aa21732caec8191969ab4b4da365215`，基线2baf35c。当前完成的是实现与预开批检查；旧P4采集保持收口，GPU/仿真/planner/训练/高清均未执行。

## 一次阅读入口

1. 本文件、`INDEPENDENT_REVIEW.md`：完成边界和发现/修正记录。
2. `SCENE_AND_RESERVE_CONTRACT.md`、`PLANNED_SLOTS_V2.json`、`RESOLVED_PRIMARY_SCENES.json`：56槽及40个具体CPU场景。
3. `CALL_CHAIN_BUDGET.json`、`F1_FIRST_WAVE/manifest.json`：实际调用预算与仅两个F1 root的执行包。
4. `PORTABLE_REPORT.md`、`FINAL_READER_REAL_SAMPLES.json`：四族真实样本及副本恢复。
5. `FAMILY_ENTRY_REPORT.md`、`NATIVE_F4_REPORT.md`、`FIRST_WAVE_LAUNCHER_REPORT.md`：实际接口、资格依赖和启动器。

## 首波包与实际命令

只登记F1_000001、F1_000002（train clear/medium），每根3意图×pc/path/motion=9条。manifest.execution_authorized和两份authorization.gpu_execution_authorized均为false，不是执行许可；配置字节、源代码、spec、预算都已绑定。无需每个helper求批，但必须另获首波及调度附录的适用授权后，重新封存授权文件哈希与manifest，不能手动绕过Guard。

当前可运行的CPU命令：

```
source /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
cd /nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910
PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin python execution_cli.py --spec F1_FIRST_WAVE/F1_000001.spec.json --describe
```

未来获批后的实际启动入口（当前false包会在GPU快照前拒绝）：

```
PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin python first_wave_launcher.py --manifest F1_FIRST_WAVE/manifest.json --state-dir /nfs_share/lijunhui/Robotwin2/datasets/formal_firstwave_f1_v1/coordinator
```

启动器复用现有GPU Guard、项目physical lease和ExecutionLedgerV2，增加UUID锁；协调者无CUDA，同族两root各固定一卡、最多两job，允许GPU0–7中任意当时独立fresh-idle卡，不等全卡。每job独立缓存/TMP、unset LD_LIBRARY_PATH、显式CUDA12.1/UUID。原P4账本不读写，旧余额不继承。F1/F4及F2/F3均使用现有pinned-renderer wrapper核对实际渲染设备。

## 新实现的实际链

- F1：`execution_cli → family_entry → native_f1/native_f1_factory → native_f1_orchestrator → f1_disk_verifier → f1_portable_export`。成熟primitive保留；参数进入真实actor/camera factory，原始观测动作前写盘读回；三个cohort组合九格。恢复只复用已通过且raw/current/anchor/prefix/源码匹配的分支，重做必要前置资格，复用不重复执行。
- F2/F3：`native_f2f3.qualify_native_root`先分别运行三程序资格；`run_native_root → native_cells → native_scenes`消费同一resolved spec派生的明确native binding。新文件沿v43动作代码派生，旧文件原样；root身份不再依赖A/B。逐cell独立验收/断点，pc严格prefix，inv分别与同程序baseline按阶段比较；F2 motion检查实际35/40帧保持，F3按原V/H/rest和分量终态门。`formal_export`封存后复制。
- F4：`native_f4_qualification`三planner+五隔离micro，重新绑定新布局；`native_f4`复用qualified suffix planner/executor与可恢复orchestrator，三cohort九格；原槽映射和抓取/执行臂profile保留，独立磁盘语义与全世界终态检查，再经统一CLI自动封存/复制。
- 所有原始时间边界先落盘再解析usage；collection计数按已创建的strict-prefix-branch场景，capture/prefix中途失败也计，不仅数成功后缀。缺时序/phase/终端证据保留reservation为未决，不猜零。

## 预算已按调用链纠正

旧708/708/540、37620solver、383400GPU秒是历史框架提案，仍未授权，不是新入口可直接派发额度。

| F1首波两root | fresh | action | collection | solver cap | GPU lease上限 |
|---|---:|---:|---:|---:|---:|
| 无恢复基数 | 66 | 42 | 18 | 384 | 不把上限当耗时预测 |
| 含每cohort一次有限恢复的预留上限 | 132 | 84 | 36 | 768 | 14400秒 |

每job预留7200s，运行timeout6500s、cleanup600s、pre/post/reap额外100s；lease按acquire到释放累计。普通CLI错误只计实际lease和可证实活动；0退出码仍须独立根验收与九格副本/registry一致才可PASS。FAILED/SOURCE_CHANGED/UNRESOLVED/OVERRUN均停新派发。外部后来占卡仅令device_idle_observed=false，不反判owned cleanup。

F1基数每root实际33 fresh/21 action/9 collection，prefix是独立参考scene，不是首条内生成。F2/F3为3资格+9采集scene，首采内生成collection prefix；F4为额外8资格scene+33 root scenes。后续族资源申请须使用当前CALL_CHAIN_BUDGET，不能套旧12scene配方。

## 首波仍需实测的假设与停点

具体布局、拥挤条件、干扰物、所有新场景IK/抓取/放置、pixel byte等价、实际耗时与RSS尚待原生GPU首波验证。CPU fixture只能证明调用/保存/验收/恢复链，不能证明机器人可行；F2/F3 fixture替换的是整个物理cell engine，原生动作内部未在CPU中执行。

首波两个完整root各9/9、同root current/anchor、pc前缀与全部变体/语义、source及副本读回、零未知预算与owned残留全部通过，才申请按冻结规则完成F1；然后F2→F3→F4。未完成root不降R、不删意图。copy失败只恢复副本，不重跑机器人。首波不证明全360已验证，不自动启动其余族或模型实验。

当前副本容器本身不授予整数据集或科学Stage1资格；其原始控制器标签保留，根的有效结论由新spec绑定的独立验收和source index给出。已有pilot/debug不自动充入正式分母。350GiB只是空间计划，个人quota未核实；共享NFS空闲约27.34TB不是配额保证。两job使CPU finalizer/copy并发至多2，RAM按24GiB/worker规划而非实测上限，首波记录真实RSS/吞吐。
