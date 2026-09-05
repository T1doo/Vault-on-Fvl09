# 最新外审执行反馈：F4 物理跑通，收据 CPU 修复已验证；F2/F3 窄边界

本轮依据用户转交 `https://chatgpt.com/s/t_6a9b97991a788191939fe2d8b6dec5d9`，已完整读取并原样保存全部 16,355 字符正文，未发现附件下载链接。前一执行批准发布 commit=`72d8d16`，F2/F3 CPU 实现发布 commit=`4a16853a616b4ad1ab845913a421050392fb3fbc`。以下是实际结果，不是新扩大授权。

## 一、最重要的新结果：F4 三条真实分支已经成功执行

批准的唯一 V2.2 root 已执行完毕，未重试：

- candidate r01；ABC / ACB / BAC；共同前缀 right arm、后缀 left arm。
- physical GPU4 UUID=`GPU-6a2b7387-0c6e-f68d-4f88-92e859c27da7`；Guard PID902392、child/PGID902448；耗时 2200.69 秒。
- 136 planner queries（10 canonical-prefix + 126 suffix）；11 unique fresh scenes；7 robot-action scenes；6 prefix replays；3 branches。
- ABC/ACB/BAC 三条 branch 均 accepted；分别 12018 / 12015 / 12049 个 26-D effective-setpoint action，主频 250 Hz。
- 3 raw、3 MP4 已完整写盘；raw manifest/payload/sidecar/NPZ/source-trace 哈希和 MP4 integrity 全部通过。
- same-current、anchor、共同前缀、selected contact identity/continuity、prior/untouched slots、common X、最终槽位、gripper open、arm neutral、final-state equivalence 全通过。
- inner `root_receipt.status=accepted`，inner root_finalization 全检查通过。
- Guard cache/lease/PID 清理完成。立即 host postcheck GPU4=12 MiB / 0% / P8、无 compute process；两个任务 PID 均已消失。

完整输出保留在 `/nfs_share/lijunhui/Robotwin2/datasets/cmf_f4_v22_authorized_root1/`。三个视频位于 `development_root/branches/F4-ABC|F4-ACB|F4-BAC/video/trajectory.mp4`。

但是不能直接称“最终 accepted root”：下面的外层收据一致性检查正确拒绝了当前磁盘状态。

## 二、外层失败不是新的物理问题，是一处 late-finalization 收据同步缺陷

外层 V2.2 finalizer 29 项 root checks 中，唯一失败是 `three_disk_branch_receipts`。每条分支的唯一失败子项是 `branch_receipt_matches_memory_and_root`。

逐层递归对比证明，每条 branch 都**恰好只有一处差异**：

```text
JSON pointer: /executed_prefix/first_post_prefix_divergence_step
disk branch receipt.json: 2851
root 内的同一 branch receipt: 2926
```

根因的源码顺序：

1. `root_orchestrator_v1_2.py:1507` 将该字段初始化为 canonical-prefix boundary=2851。
2. `root_orchestrator_v1_2.py:1691` 把 branch receipt 写盘，并保存 branch terminal event。
3. 三条完成后调用 `finalize_three_branch_root_v1_1`。
4. `root_orchestrator_v1_1.py:269` 的 `resolve_first_post_prefix_divergence` 比较三条实际 suffix step hashes，在内存原地更新三份 branch 字段为2926。
5. v1.2 最后只发布 root receipt，漏掉 late-finalization 后同步 branch 的步骤。对照 v1.1，其对应路径有重新发布分支的循环。

本轮没有修改这些 sealed source，也没有覆盖原 branch/root/job receipt。外层 exact equality 的拒绝本身是正确的，不能靠忽略字段、放宽容差或删掉 check 让它通过。

原 job terminal 因此仍为 `pass=false`、accepted development=0 roots/0 trajectories、error=null，child exit1。POST_CHILD `validation_pass=true, job_succeeded=false`；Guard cleanup 完整。请保留这个负结果，不删除或伪装成当时已经成功。

## 三、已完成的 CPU-only 修复验证：不需要第二次物理 root

新增只读脚本 `f4_receipt_divergence_resolution_cpu_v1.py`，结果为 `F4_ROOT1_DIVERGENCE_RECEIPT_RESOLUTION_CPU_V1.json`。

它完成了以下独立核验：

1. 从三个 immutable raw NPZ 直接读取 `stream__controller_effective_setpoint`。
2. 重算每步 suffix SHA，与每份原 branch receipt 的完整 `post_prefix_action_step_sha256` 一致。
3. 直接比较三 raw 的首分歧，结果=2926；旧 resolver 在深拷贝 receipt 上的结果也=2926；与 root receipt 一致。
4. canonical P 仍为2851，真实 suffix 开头还有75步共同动作；这不是修改 P、补 hold、重采样、修改 H-view 或更改动作。
5. 仅构建单字段派生 view，绑定原文件 SHA；要求改后所有字段与 root 完全一致。没有真实文件替换。
6. 五项负例全部拒绝：错误原 hash、错误 divergence、额外 status 变化、canonical P 变化、bool 冒充整数。
7. 在只读诊断中给未修改的 V2.2 finalizer 提供这些明确标记的派生 view，其余 raw/video/root 均从真实磁盘读取，所有检查通过。
8. 再次 hash 所有相关原 artifact，字节完全不变。

这只证明单字段 CPU 收据修复方案能通过同一验收逻辑；**不是原文件已修复，也不是已采纳新的 accepted root**。machine receipt 的 `adoption_authorized=false`、`original_terminal_superseded=false`、`proposal_accepts_development_root=false` 都保持。

### 请求 A：仅批准这次数据的 append-only CPU receipt resolution

建议精确决定：`APPROVE_F4_ROOT1_CPU_ONLY_RECEIPT_RESOLUTION_V1`。

期望批准范围仅限：

- 使用已有 3 raw / 3 MP4 / 原 branch+root+job+Guard receipts；0 GPU、0 scene、0 planner query、0 physical、0 new trajectory。
- 新版本 resolution receipt / derived branch views / post-resolution acceptance receipt，全部绑定原文件 SHA、实际 raw-derived2926与原 canonical P2851。
- 只允许上述 JSON pointer 从2851解析为2926，其余任何变化拒绝。
- 保留原 job pass=false 和 Guard exit1 的历史；以新 receipt 说明“原运行物理成功、收据同步后通过”，不篡改当时终端。
- 新 finalizer 读取语义必须显式识别原收据+合法 resolution，而不是默默替换文件、删检查或忽略差异；仍重新检查全部 raw/video/current/anchor/prefix/final-state/accounting/cleanup。
- 只有上述复核通过后，才能把 development accepted 增加 1 root / 3 trajectories；仍不 promotion 到 Stage1/formal，不授权下一 root。
- 暂不改 active collector 或重新收集。对未来 collector 的 late-finalization publication 修复另行版本化，不能回写已封存数据。

本次 root 已消费其唯一授权，**不申请也不需要再次跑 F4 物理任务**。

## 四、F2/F3 的独立进展与请求

详细来源和源码入口见 `GPT_REVIEW_REQUEST_F2_GEOMETRY_F3_MICRO_20260905.md`，本轮已 push。

F2：保留 Run3 inside5/5；新增几何语义修复和 finally cleanup receipt，9/9 CPU tests。发现上一外审引用 collision inventory 的中心，与 live helper 实际使用 model_data centre/extents 不同：外审 XY 补偿为约(+3.619492,+2.966821) µm，实际 metadata 为(-9.404122,+10.797513) µm。后者重算的 actor pose 与历史 candidate0→2 整体平移完全一致、table plane=0.74、composed centre XY正好candidate2。没有放宽容差、换来源、重跑 inside，beside GPU仍未启动。

请求 B：明确是否保留 live metadata 来源并纠正前述示例数值，再按原条件许可完成 beside-only 6 queries / 1 scene 的执行入口、预检、发布和单次运行。若要求换 collision bounds，需单独影响审计，不冒充几微米口径修复。

F3：原 V1.1 full-window Gate 不变，四exact recipes已解析冻结；新 candidate-bound executor/Guard/runner实现并通过23 runtime tests、8 window tests和真实CPU Guard→runner→4 Stage-A bound-spec构建。完整CPU receipt还绑定F2的9 tests。没有新F3 GPU/physical。

请求 C：窄复审新 F3 runtime；通过后才单独批准 `F3_PRECLOSE_CANDIDATE_MICRO_EXECUTION_V1`，绑定 proposal exact `candidate_freeze_sha256/caps/source_files`，预算仍52 queries / 12 scenes / 4 attempts、两次micro pass立即停，shared-V/no-suffix/root/raw/formal=0。不要把这次CPU tests升级为新候选可抓取的证明。

## 五、关键机器证据与统一状态

| 文件 | Receipt SHA-256 |
| --- | --- |
| F4_V2_2_ROOT1_TERMINAL_PUBLICATION_20260905.json | e1bc38bd288a56dbc1cd0f4b14959f86795a8b5c2aca75e9216d3b8795e00b45 |
| F4_ROOT1_DIVERGENCE_RECEIPT_RESOLUTION_CPU_V1.json | bd2a313764f0cae98340e93c54d3fc784a7a7bc1061eee9655e43af46ba7ecbf |
| F2_F3_CPU_IMPLEMENTATION_REVIEW_20260905_V1.json | 566ee8ec93cd3ee1957a1ac44d1342b4cf217b34a1056495155d9e35527d52d4 |
| STAGE1_READINESS_AFTER_F4_ROOT1_RECEIPT_SYNC_20260905.json | 13d6ee408d72227f3f522729b2b113d31930c95d620a325b80c50ea79a9dac35 |

当前最终 accepted development 仍5 roots/15 trajectories（F1）；F4三条新数据单列为物理/raw通过、外层收据修复待采纳。Stage1 accepted authorized=0/48；formal=0/40 roots、0/360 trajectories。F1已补CPU invariance设计但未收集新的realizations。

Stage0保持封存。GPU jobs按最新外审串行，任何新GPU只用live fresh-idle物理0–7且完整Guard/UUID/lease/pre-post/cleanup。Stage1、formal360、训练、H-reveal、compression、π0.5均未授权。
