# F1–F4 additive 代码审阅快照

该目录是为外部 GPT 通过 GitHub 审阅而创建的只读快照。

- 快照来源：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/controlled_multi_future/`
- 测试来源：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/`
- official baseline：RoboTwin `c3ddfa8b97d5519efa828b075999bd0006778e5e`
- 当前快照日期：2026-08-28
- 当前 GPU-preflight CPU/static 实现版本：`controlled_multi_future_runtime_v3_1`；科学设计版本仍为 `controlled_multi_future_f1_f4_v1_2`。
- Git 状态：active additive source 仍是 RoboTwin 工作树中的 untracked directories；官方 tracked baseline 零修改。

本快照不是 active source，不应直接用于运行、Stage 0 或 formal collection。审阅意见应先应用到 active RoboTwin source，重新测试并生成新快照；不要在 Vault 副本中独立演化实现。

目录内容：

- `controlled_multi_future/base.py`：统一 fail-closed lifecycle interface；
- `schemas.py`：最小 schema/contract checks；
- `candidate_freezer.py`、`current_hasher.py`、`anchor.py`：candidate/current/anchor freeze 与 equivalence；
- `geometry.py`、`runtime_v2_contracts.py`：actor→EEF、真实 cavity/footprint、swept-path 与 runtime-v2 历史 repair 合同；
- `runtime_v3_contracts.py`：F1 三分支、F2 固定 workspace candidates、F3 release diagnostics 与 F4 segmented routes 的当前 CPU contracts；
- `runtime_v3_1_contracts.py`：executed-prefix、chained planner、grasp-slip、fresh-route 与 A0 budget 的 GPU 前加固合同；
- `probe_contracts.py`：无 RoboTwin runtime 依赖的 current/historical variant 与 semantic-result contracts；
- `raw_writer.py`、`receipts.py`、`attempt_state_machine.py`、`finalizer.py`：250 Hz 26-D、N actions/N+1 states 的 raw-v2_1 attempt pipeline；
- `pilot_pipeline.py`：正式采集关闭状态下的 Stage-0-shaped nonformal integration orchestrator；
- `root_orchestrator.py`：保留的 runtime-v3 历史 synthetic root contract；其中 real adapter 未实现，不能作为 current v3_1 入口；
- `root_orchestrator_v1_1.py`：task/physical 与 planner 分账、唯一 scene cleanup receipt、immutable program/spec、provisional artifacts、actual-prefix 与独立 root finalizer；
- `real_sapien_adapter_v1_1.py`、`family_runners_v3_1.py`、`family_repair_orchestrator_v1_1.py`：延迟导入的真实 RoboTwin adapter、F1 root runner 和 F2/F3/F4 repair runner；尚未获得 GPU runtime evidence；
- `families/`：F1–F4 frozen program skeletons；
- `signals.py` 与 `verifiers/`：pure signal/verifier adapters；
- `probes/action_feasibility.py`：旧 bounded repair v1，只保留历史实现，CLI 已 fail-closed 禁止重跑；
- `probes/action_feasibility_v2.py`：runtime-v2 的 F1/F2/F3/F4 单 gate runner；runtime-v2 budget 已在 GPU1 执行并耗尽，不得重跑；
- `probes/` 其他模块：cleanup-safe lifecycle、scene inspection、真实 trace/raw adapter、atomic GPU guard 与 synthetic pipeline dry-run；
- `tests/controlled_multi_future/`：CPU static/pipeline contract tests（当前 70 tests）。

在 Vault 根目录复核快照测试时，需要把本目录加入 import path：

```bash
PYTHONPATH='数据构造/实现审计/代码审阅快照' \
  /nfs_share/lijunhui/Robotwin2/env/bin/python \
  -m unittest discover \
  -s '数据构造/实现审计/代码审阅快照/tests/controlled_multi_future' \
  -p 'test_*.py'
```

运行证据、截图、receipts 和 realized NPZ traces 不复制到本目录，统一位于相邻的 `../probe_outputs/`。Runtime-v2 实际结果见 `../runtime_v2_bounded_probe_execution_report_20260828.md/json`；runtime-v3_1 current synthetic evidence 为 `../probe_outputs/nonformal_root_pipeline_dry_run_runtime_v3_1_20260829_cpu4/`。真实 A0／family GPU evidence 仍为 0，Stage 0 仍为 `BLOCKED_WITH_REASONS`。
