# Development Pipeline Consolidation and Template Convergence V1

终态：`COMPLETED_WITH_BOUNDED_SEARCH_EXHAUSTION`

## 结论

1. Canonical serialization 已统一到 `controlled_multi_future/canonical_artifact.py`；NumPy scalars/arrays 可规范化，NaN/Inf/unsupported object fail closed，无 `str(obj)` fallback。
2. F1 未 redesign，既有 5/5 development roots、15/15 trajectories、15 raw、15 MP4、15 verifier pass 保持不变。
3. F2 rank50–61 已完整按序运行，终态为 `ALL_12_DYNAMIC_CANDIDATES_EXHAUSTED`，没有 passing binding，也没有 inside/on/beside three-branch root。
4. F3 12/12 official grasp candidates planner-screen pass；按 rank 实测 r01–r04。r01/r02 在 pre-V grasp/contact/off-support Gate 失败，r03/r04 在 pregrasp planner control 失败。
5. F3 stable grasp=null；没有运行 3-scene confirmation，也没有形成 VVHH/VHVH/VHHV root。终态为 `BOUNDED_GRASP_SEARCH_EXHAUSTED_REQUIRES_ASSET_REDESIGN`。
6. F4 c01–c06 均完成。所有已观察的 reference/planner-current rendered visibility receipts 通过，但六项都在 ABC 首个 `A_pregrasp` chained planner failure，未形成完整 A/B/C endpoint/neutral-chain matrix。
7. F4 selected template=null；没有运行 A-only，也没有形成 ABC/ACB/BAC root。终态为 `BOUNDED_LAYOUT_SEARCH_EXHAUSTED_REQUIRES_HIGHER_LEVEL_LAYOUT_REDESIGN`。

## F2候选终态

- rank50–54：passive-on/layout pass；inside planner IK failure。
- rank55–59：passive-on angular stability failure，未进入 planner。
- rank60–61：passive-on support、linear stability、angular stability failure，未进入 planner。
- Counts：125 planner queries、5 prefix references、0 branch executions、0 recovery、52 fresh scenes。

## F3候选终态

| Candidate | Planner queries | Physical attempts | Result |
|---|---:|---:|---|
| r01 | 7 | 1 | pre-V drift/contact/off-support failure |
| r02 | 7 | 1 | pre-V drift/contact/off-support failure |
| r03 | 2 | 1 | pregrasp planner-control failure |
| r04 | 2 | 1 | pregrasp planner-control failure |

加 planner screen 共 20 planner queries、4 physical attempts、5 fresh scenes。

## F4候选终态

| Candidate | Observed visibility | Prefix refs | Planner queries | First failure | Template pass |
|---|---|---:|---:|---|---|
| c01 | PASS | 1 | 11 | ABC/A_pregrasp | false |
| c02 | PASS | 1 | 11 | ABC/A_pregrasp | false |
| c03 | PASS | 1 | 11 | ABC/A_pregrasp | false |
| c04 | PASS | 1 | 11 | ABC/A_pregrasp | false |
| c05 | PASS | 1 | 11 | ABC/A_pregrasp | false |
| c06 | PASS | 1 | 11 | ABC/A_pregrasp | false |

总计 66 planner queries、6 prefix references、12 fresh scenes、0 suffix execution、0 release execution。因首段 fail-fast，未观察的 A/B/C endpoints 明确记录为未通过/未完成，不能用 observed visibility PASS 冒充 template-qualified。

## GPU与cleanup

共 12 个 guarded jobs：F2×1、F3×5、F4×6。使用 physical GPU0/1/2/3，均由实时 fresh-idle snapshot、UUID binding、one job/card、lease、source lock、isolated cache 和 post-release Guard 约束。12/12 Guard completed；child exit=0；timeout=false；task-owned cleanup=true；orphan=0；post-source-lock=true。10/12 明确返回 idle baseline；c03/c04 释放后外部 STAR 进程立即进入 GPU1/2，因此两项记录 `external_process_detected_after_release=true`、idle-baseline=false，但外部进程未被修改且本任务无残留。

## 汇总计数与科学边界

- Planner queries：211。
- Controlled prefix/qualification executions：15（F2 prefix 5、F3 physical 4、F4 prefix 6）；branch/suffix executions=0；新 development trajectories=0。
- Fresh scenes：69。
- Formal roots/trajectories increment：0/0。
- F2 blocker：当前冻结 asset/layout set 无全 Gate passing candidate；只支持更高层 asset/layout redesign，不证明所有资产都失败。
- F3 blocker：当前 `001_bottle/base13` 官方候选族无稳定 program-independent nuisance grasp；尚未测试 temporal-order mechanism。
- F4 blocker：当前六布局都在共同 A_pregrasp endpoint 失败；需要更高层 source/layout/grasp redesign，尚未测试 high-level order mechanism。

## 最终验证与授权边界

- Active full suite：667/667，466.069 s。
- Snapshot full suite：667/667，437.154 s。
- Compile：PASS；active/snapshot byte-equal。
- Implementation source SHA-256：`8cd65541437555e84654fd8d70267a42443f0b5e09b00c5062a3741b82a88eb1`。
- Tests tree SHA-256：`ecf7fbf56a55b4e60de9748e636407e8455807e5fe70bfcfd074227766de1000`。
- Machine report payload：`a77d2b8f3d4c621303612f1bdc9500ee6251fd96cedbbb7b5668359b21400fe7`。

Stage 0 seal保持不变。Canonical Stage 1、formal 360、训练、H-reveal、compression 与 π0.5 仍未授权。
