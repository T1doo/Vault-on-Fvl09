# F4 Runtime V2.1 final CPU publication review V2

日期：2026-09-04

状态：`PASS_READY_FOR_NEW_EXTERNAL_REVIEW_NO_EXECUTION_AUTHORITY`

本文档只封存 F4 Runtime V2.1 的 CPU publication 证据。它不是 GPU、planner、
physical scene 或 development root 执行授权。

## Source freeze

- Vault source commit：`10d4ec85a02e4d0bf47bee65d7022bb46f6aa98b`
- `main` 与 `origin/main` 在生成时均指向上述commit。
- RoboTwin tracked HEAD 仍为 `c3ddfa8b97d5519efa828b075999bd0006778e5e`。
- Runtime V2 和 active RoboTwin scientific/physical source 未修改。

Runtime V2.1 文件：

- `manifest_contract.py`：`eb6afbb96d4737946dd8de8d527fc41afee98fac762fb3a1255ba877c5a06b4f`
- `guarded_launcher.py`：`1dd8188da117876b4b452b8dc96d5b35cf8d49d0daff190ed5eac9ffb9bb5454`
- `job_runner.py`：`7b47e1a7e3ad9fd0db528e23ee9d870029d527c5b2f47a3550fc545d3a257463`
- `lifecycle_preflight.py`：`fcb125438d19f71ff9a31ad353b7481935290c0f36a64e0e1427225369c5f0a1`

## Machine hardening result

`F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_FINALIZER_TEST_V1.json`：

- receipt SHA：`1c546ace3994e5d2afb46f7490b6d0d3e55d9b666cb41e9cc54658bbe4b723f2`
- file SHA：`88c9b4d94158d724dc520898d0ee48196851e86fcaac18ad986725183a7ab6f1`
- finalizer：`18/18`
- runner environment negatives：`21/21`
- lineage negatives：`5/5`
- executable identity negatives：`3/3`
- POST_CHILD：`11/11`
- NumPy serialization：PASS

它覆盖 accepted 3/3、failed verifier、raw/MP4/root/branch 损坏、协调替换 raw
NPZ+manifest+sidecar、额外null branch、branch倒序、重复feasibility program ID、
suffix/planner计数、duplicate scene、phase multiset、planner delta、final-state
equivalence和NumPy序列化。所有新增负例均fail-closed。

## Proposal V2

`PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_MANIFEST_V2.json`：

- manifest SHA：`ea27ac315516b2006a96bd92594e125473970d111d2ef12434be9fecc11893e5`
- file SHA：`751ff914161456a70dd2975ada2de5f8b4aa7f70edcad2abd8291708e44d8612`
- status：`PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2`
- `approved=false`
- GPU/planner/scene/physical/root execution 全部`false`
- 无root-execution approval lineage。

Proposal保持下列scientific contract不变：

- candidate：`f4-slot-corridor-hv2-r01`
- programs：`F4-ABC / F4-ACB / F4-BAC`
- arms：canonical prefix=`right`，program suffix=`left`
- planner cap：`10 + 3 × (12 + 30) = 136`
- fresh scenes=`11`，robot-action scenes=`7`
- branches/raw/MP4/development trajectories=`3/3/3/3`
- accepted development roots≤`1`，formal trajectories=`0`
- no retry、fallback、seed retry、candidate search、second root或root sharding。

## Exact PREPUBLICATION validation

`F4_INFRASTRUCTURE_CORRECTED_ROOT_PROPOSAL_V2_PREPUBLICATION.json`：

- receipt SHA：`a585de409f4fb857ee14cf8499335e697946359457b10892d60abf5405a3f5a9`
- file SHA：`0a8ada6fb9cd69beb13bc7508e565c9a07a6b52819d0f1484a513b3864a3705b`
- 真实 V2.1 `load_and_validate_manifest_job(...)`、phase=`PREPUBLICATION`
- `require_execution_authorized=false`
- latest external decision、source proposal V1、Runtime V2 CPU review/lifecycle 和
  V2.1 hardening receipt 全部exact-bound。
- output、Guard directory和cache-job在验证前后均不存在。
- `root_execution_approval_bound=false`。

CPU review machine receipt：
`F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_CPU_REVIEW_V2.json`

- receipt SHA：`f1efa1fa8e093a2ca900171cab9cd72d1fb1f44f5ffbca2fff398aa58a1db166`
- file SHA：`0ff6f2a68ca25f0686e1673f8951b000e31d2a84ce6a5690666477cb238bb51a`
- all checks：PASS

## Execution boundary and next action

本轮调用为 `0 real lease / 0 nvidia-smi / 0 GPU context / 0 scene / 0 planner /
0 physical / 0 root / 0 production output / 0 authorization consumption`。

下一步只能将Runtime V2.1 hashes、hardening test receipt、proposal V2和本CPU review
交给新的外审。外审如未另行明确批准一个F4 development root，本地不得创建
`approved=true` manifest，也不得启动F4 GPU。
