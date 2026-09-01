# Development Pipeline Consolidation V1：CPU Freeze

状态：`CPU_AND_SNAPSHOT_FROZEN_GPU_NOT_STARTED`

## 已冻结内容

- 唯一 canonical JSON/hash/write/self-hash 实现为 `controlled_multi_future/canonical_artifact.py`。
- F1 不做模板 redesign；既有 5 个 development roots / 15 条 trajectories 保持不变。完整冻结合同 canonical SHA-256 为 `60d303df5392b139eac29ed189e287e77988c08b6ee7554e1e4b1941451a78e7`。
- F2 只允许冻结 matrix/screening 的 rank 50–61 原样重放，选择首个通过全部旧 Gate 的 rank；不得改变资产、layout、planner、verifier、threshold 或 release。
- F3 预注册 12 个官方 contact/rotation grasp candidates；先完整 planner screen，最多 4 个真实 physical candidates，按最低 passing rank 选择，再做 3 fresh scenes 和条件式完整 root。
- F4 预注册现有 6 个 CPU-passing layouts（上限保持 12）；所有候选均须形成 visibility / A-B-C endpoint IK / complete chain 矩阵，按最低 passing rank 选择，再做 A-only 和条件式完整 root。

## CPU 与快照证据

- Active full suite：`665/665`，136.569 s。
- Snapshot full suite：`665/665`，136.516 s。
- Active/snapshot source and tests：逐文件相等，compile 通过。
- Implementation source SHA-256：`061eec77da8ba3e124f79690761df436328b1777123b850777b33966ea176b0a`。
- Tests tree SHA-256：`75038b3c76bc9d8cd9bd1b93f2323033de99e1a0a1a5246a08935854543b4f02`。
- Machine report：`DEVELOPMENT_PIPELINE_CONSOLIDATION_V1_CPU_FREEZE_REPORT.json`，payload `ac3a6758d1b35b14fd0998cbe823d349061dc4ff4df83dd0c700d74f53068e16`。

## 当前边界

本工作包尚未启动任何 GPU job、未生成新 trajectory，也未改变 Stage 0 seal。Stage 1、formal 360、训练、H-reveal、compression 与 π0.5 继续禁止。

下一安全步骤是先提交并 push 本 CPU freeze，使 source-bound authorization 绑定 clean published Vault HEAD；随后 fresh scan GPU0–7，并由每个 job 的 Guard 执行 UUID、lease、pre/post、source-lock 与 ownership-scoped cleanup。
