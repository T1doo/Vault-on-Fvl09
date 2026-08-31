# 当前 GPU0–7 并行执行策略审计（v2）

## 当前裁决

```yaml
host: fvl05
policy_version: cmf_gpu_parallel_policy_v2
allowed_physical_gpu_indices: [0, 1, 2, 3, 4, 5, 6, 7]
dynamic_fresh_idle_selection: true
parallel_different_cards_authorized: true
one_project_job_per_gpu: true
one_root_one_gpu: true
root_sharding_authorized: false
automatic_gpu0_fallback: false
new_gpu0_only_authorization_allowed: false
```

GPU0没有优先权，也不是唯一设备。任意一张GPU只有在该job启动前由完整实时snapshot和atomic Guard证明independently fresh-idle，且UUID与authorization一致时才可使用。不同root/job可在不同卡并行；同一root不跨卡拆分。

## 已定位的旧问题

1. Stage 0执行时，Codex会话启动阶段缓存了一份迁移旧`AGENTS.md`的GPU0-only指令。磁盘上的规则后来虽已改为GPU0–7，但已经注入会话/审批器的instruction snapshot不会热刷新，因此GPU4 launch被外部审批器拒绝，四family最终在GPU0串行。
2. 历史`stage0_smoke_parallel_scheduler_v1/v1_1`要求四张卡同时空闲；少于四张时返回零assignment。它适合一次性四family wave，却不适合作为后续批量生产的current scheduler。
3. 若只更新文档而不建立机器Gate，新authorization仍可能误写成`[0]`，再次造成静默串行。

这些旧authorization、receipt和执行报告是历史事实，不修改、不重新签名。它们不再定义新job的设备范围。

仍含GPU0-only字样的active Python文件只有历史版本入口：`pre_stage0_authorization_v3.py`、`runtime_v3_3_scope_bundle_v1.py`、`probes/runtime_v3_3_authorization_v1.py`与`probes/runtime_v3_4_1_authorization_v1.py`。它们分别绑定已终止的Revision-9/v3_4_1 one-shot证据，禁止作为新job模板。第五个命中文件是current `gpu_parallel_policy_v2.py`自身对“拒绝GPU0-only”的错误消息，不是设备限制。

## 当前实现

Active source新增：

```text
controlled_multi_future/gpu_parallel_policy_v2.py
```

它提供：

- `validate_current_gpu_authorization()`：新授权必须精确允许GPU0–7，并明确并行、一卡一job、root不shard、无GPU0 fallback；`[0]`会fail closed；
- `schedule_dynamic_gpu_wave()`：一张卡空闲就调度一个job，多张卡空闲就组成同等规模的并行wave，不再等待四张同时空闲；
- 完整GPU0–7 snapshot、UUID唯一性、≤15秒scheduler snapshot age、P8、≤100MiB、≤1% utilization、无compute process检查；
- scheduler只做候选分配，不消费one-shot authorization、不声称reservation；每个child启动前仍必须由Guard重新snapshot、获取per-GPU lease并绑定UUID。

CPU tests覆盖：

- GPU0忙、GPU2/5/7空闲时直接调度2/5/7；
- 仅GPU6空闲时立即调度一个而不是等待四卡；
- GPU1/3/4/7空闲时并行调度四个不同root；
- 无空闲卡时不消费authorization；
- stale snapshot、重复root/output、GPU0-only authorization均拒绝；
- scheduler不会把assignment伪装成reservation。

Focused tests=`8/8 passed`；完整active suite=`520/520 passed`；181个source和93个test Python文件compile通过。

## 外部审批层验证边界

2026-08-31 12:27 CST的只读全卡查询已由执行审批器批准：GPU0–7均约12–15MiB、0%、P8，compute process列表为空。首次尝试physical GPU7单张量测试时，审批器仍引用本会话启动时缓存的旧GPU0-only instruction而在process creation前拒绝。用户随后对已披露的GPU7 micro-test作精确批准，审批器已允许非零GPU实际执行。

实机验证分两步：第一次Python启动在导入PyTorch时误加载共享`/share/apps/cuda/12.2/lib64/libnvJitLink.so.12`并I/O error，尚未初始化CUDA，GPU7仍为14MiB/0%/P8。按现有Guard环境合同清除`LD_LIBRARY_PATH`、固定项目CUDA 12.1并继续绑定GPU7 UUID后，第二次成功：

```text
physical_gpu_index = 7
gpu_uuid = GPU-4c836e67-fb8e-a993-002c-cb83b10a6ead
child_pid = 288238
torch.cuda.is_available = true
visible_device_count = 1
logical_device_name = NVIDIA RTX A6000
cuda_tensor_result = 1.0
postcheck = 14 MiB / 0% / P8 / no GPU7 compute process
```

运行时GPU0–3已有其他compute jobs，GPU7仍独立空闲；本任务未共享、停止或干预这些进程。这直接证明GPU0忙时可在非零空闲卡上安全运行，且执行审批、UUID映射、项目CUDA环境与post-release链路均可用。

因此当前状态是：

```text
on_disk_policy_and_scheduler = fixed_and_cpu_verified
current_session_nonzero_gpu_runtime_proof = passed_on_physical_gpu7
external_approval_integration = passed
project_cuda_environment_contract = passed
```

本验证不构成GPU reservation或后续job的空闲证明。未来每个wave和child仍必须重新执行完整live snapshot、atomic Guard、UUID、lease、timeout、cleanup和post-release审计。

本策略修复不授权Stage 1、formal collection、训练、H-reveal、compression或π0.5，也不允许重跑已终止Stage 0 attempts。
