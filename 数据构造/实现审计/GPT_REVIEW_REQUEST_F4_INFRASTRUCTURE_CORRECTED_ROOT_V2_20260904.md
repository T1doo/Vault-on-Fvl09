# GPT review request: F4 Runtime V2.1 final CPU hardening

请对 F4 Runtime V2.1 做一次窄范围、独立的最终外审。

本请求文件不是执行授权。当前proposal中 `approved=false`，GPU、planner、scene、
physical、root execution均为`false`；Codex本地不得因为本文档而启动F4 GPU。

## Review base

- Vault source freeze：`10d4ec85a02e4d0bf47bee65d7022bb46f6aa98b`
- 生成publication时 `main == origin/main == 10d4ec85...`
- latest external decision：
  `EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_20260904.md`
- decision file SHA：`790fc6e3e48694d212bb1c1a8833d270f2dc0dbe4748a605f319003787fd0dcd`
- decision receipt SHA：`c8ff692590d7cdb63995c9ce6932d851c1ef918fb5a8e8003881d2035eca7c35`

## Only four publication items need review

### 1. Runtime V2.1 hashes

- contract：`eb6afbb96d4737946dd8de8d527fc41afee98fac762fb3a1255ba877c5a06b4f`
- Guard：`1dd8188da117876b4b452b8dc96d5b35cf8d49d0daff190ed5eac9ffb9bb5454`
- runner：`7b47e1a7e3ad9fd0db528e23ee9d870029d527c5b2f47a3550fc545d3a257463`
- lifecycle：`fcb125438d19f71ff9a31ad353b7481935290c0f36a64e0e1427225369c5f0a1`

Implementation review：
`F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_IMPLEMENTATION_REVIEW_20260904.md`，
file SHA=`419750d638252a7fdeeb663816a8f373470e05552461d0a93c6b055bdc911c38`。

### 2. Machine hardening receipt

`F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_FINALIZER_TEST_V1.json`：

- receipt SHA=`1c546ace3994e5d2afb46f7490b6d0d3e55d9b666cb41e9cc54658bbe4b723f2`
- file SHA=`88c9b4d94158d724dc520898d0ee48196851e86fcaac18ad986725183a7ab6f1`
- finalizer=`18/18`
- environment/lineage/identity/POST_CHILD=`21/21, 5/5, 3/3, 11/11`
- execution-authorized synthetic fixture在real lease/nvidia/CUDA/scene/planner/output之前停止。

请特别确认：

- latest decision/source proposal V1/CPU review/lifecycle receipt的exact lineage绑定；
- Guard/runner/contract `__file__` identity；
- RUNNER_ENTRY的start/GPU UUID/index/lease/CUDA/PYTHON/9-cache/no-LD binding；
- POST_CHILD的exit/job/finalizer/1+3/cleanup/GPU-baseline等价性；
- root/branch/raw/MP4/suffix/scene phase的独立磁盘复验；
- cross-audit新增四个负例已拒绝：coordinated raw replacement、extra null
  branch、reversed branch order、duplicate feasibility program IDs。

### 3. Proposal V2

`PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_MANIFEST_V2.json`：

- manifest SHA=`ea27ac315516b2006a96bd92594e125473970d111d2ef12434be9fecc11893e5`
- file SHA=`751ff914161456a70dd2975ada2de5f8b4aa7f70edcad2abd8291708e44d8612`
- status=`PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2`
- no root-execution approval lineage
- all execution authorization flags=false

请确认scientific contract没有变：

- candidate=`f4-slot-corridor-hv2-r01`
- programs=`F4-ABC/F4-ACB/F4-BAC`
- arm schedule=`right prefix / left suffix`
- 无layout、physical code、planner terminal、threshold、verifier、seed或fallback修改
- caps=`1 root / 1 canonical prefix / 3 suffix preflights / 3 branch executions /
  136 planner queries / 11 fresh scenes / 7 action scenes / 3 raw / 3 MP4 /
  1 accepted development root / 3 accepted development trajectories / 0 formal`

### 4. PREPUBLICATION and CPU review V2

`F4_INFRASTRUCTURE_CORRECTED_ROOT_PROPOSAL_V2_PREPUBLICATION.json`：

- receipt SHA=`a585de409f4fb857ee14cf8499335e697946359457b10892d60abf5405a3f5a9`
- file SHA=`0a8ada6fb9cd69beb13bc7508e565c9a07a6b52819d0f1484a513b3864a3705b`
- real V2.1 contract `PREPUBLICATION` pass
- `require_execution_authorized=false`
- output/Guard/cache-job前后均absent
- `root_execution_approval_bound=false`

`F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_CPU_REVIEW_V2.json`：

- receipt SHA=`f1efa1fa8e093a2ca900171cab9cd72d1fb1f44f5ffbca2fff398aa58a1db166`
- file SHA=`0ff6f2a68ca25f0686e1673f8951b000e31d2a84ce6a5690666477cb238bb51a`
- Markdown review file SHA=`abb8bdae92713e1c48d3ca4959ce472b76d3c4ca14d7c44aeff6f44929543e3c`
- all machine checks pass

## Requested decision

请只在上述四项内决定，不需要重新研究Run9–Run14或重新设计物理任务。

如果全部通过，请明确返回唯一决策token：

`APPROVE_ONE_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2`

并在决定中绑定source commit、proposal manifest/file SHA、Runtime V2.1 四个SHA和
hardening receipt/file SHA。该决定最多只可批准上述一个nonformal F4 development
`r_pc` root，不得扩展为Stage 1、formal 360、training、H-reveal、compression或π0.5。

如果仍有缺口，请返回`REVISE`并列出精确文件、字段、失败路径和最小修复；
请不要使用模糊的“再加强一些”作为结论。

在新外审决定被完整导入、封存并生成单独`approved=true` manifest之前，
F4 GPU 仍严格禁止。
