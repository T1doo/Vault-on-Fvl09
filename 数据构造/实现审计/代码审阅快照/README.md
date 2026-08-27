# F1–F4 additive 代码审阅快照

该目录是为外部 GPT 通过 GitHub 审阅而创建的只读快照。

- 快照来源：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/controlled_multi_future/`
- 测试来源：`/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/`
- official baseline：RoboTwin `c3ddfa8b97d5519efa828b075999bd0006778e5e`
- 快照日期：2026-08-27
- Git 状态：active additive source 仍是 RoboTwin 工作树中的 untracked directories；官方 tracked baseline 零修改。

本快照不是 active source，不应直接用于运行、Stage 0 或 formal collection。审阅意见应先应用到 active RoboTwin source，重新测试并生成新快照；不要在 Vault 副本中独立演化实现。

目录内容：

- `controlled_multi_future/base.py`：统一 fail-closed lifecycle interface；
- `schemas.py`：最小 schema/contract checks；
- `families/`：F1–F4 frozen program skeletons；
- `signals.py` 与 `verifiers/`：pure signal/verifier adapters；
- `probes/`：GPU environment、scene inspection 与 finite action probes；
- `tests/controlled_multi_future/`：CPU static contract tests。

在 Vault 根目录复核快照测试时，需要把本目录加入 import path：

```bash
PYTHONPATH='数据构造/实现审计/代码审阅快照' \
  /nfs_share/lijunhui/Robotwin2/env/bin/python \
  -m unittest discover \
  -s '数据构造/实现审计/代码审阅快照/tests/controlled_multi_future' \
  -p 'test_*.py'
```

运行证据、截图、receipts 和 realized NPZ traces 不复制到本目录，统一位于相邻的 `../probe_outputs/`。完整结论与 blockers 见 `../implementation_audit_report.md` 和 `../stage0_readiness_report.md`。
