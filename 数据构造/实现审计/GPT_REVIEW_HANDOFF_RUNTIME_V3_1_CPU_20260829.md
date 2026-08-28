# GPT 审阅入口：runtime-v3_1 GPU 前加固

## 定位与当前裁决

- Repository：`https://github.com/T1doo/Vault-on-Fvl09`
- Branch：`main`
- 本轮 content commit：`PENDING_CONTENT_COMMIT`
- Design：`controlled_multi_future_f1_f4_v1_2`
- Implementation：`controlled_multi_future_runtime_v3_1`
- 当前裁决：`BLOCKED_WITH_REASONS`
- `gpu_probe_authorized=false`
- `stage0_authorized=false`

本轮只落实上一份完整 GPT review 的 CPU/code 修正。没有查询或使用 GPU，没有运行 A0、真实 SAPIEN scene、family repair、Stage 0 或训练。

## 建议阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. 本文件
4. `数据构造/实现审计/controlled_multi_future_runtime_v3_1_implementation_proposal.md/json`
5. `数据构造/实现审计/pilot_attempt_budget_runtime_v3_1_proposal.md/json`
6. `数据构造/实现审计/f1_f4_implementation_registry_v3_1_cpu_current.md/json`
7. `数据构造/实现审计/stage0_readiness_report_runtime_v3_1_current.md/json`
8. `数据构造/实现审计/runtime_v3_1_cpu_static_audit_20260829.json`
9. `数据构造/正式数据构造日志.md` 的 runtime-v3_1 追加章节
10. `数据构造/实现审计/代码审阅快照/`

## 对上一轮审阅的逐项响应

### Raw v2_1_1

- `DenseTraceMixin` 从真实 `SAPIEN Scene.get_timestep()`读取 timestep，拒绝仅用 step index 自证 250 Hz；
- manifest 强制 `simulator_timestep_seconds=0.004`、`control_steps_per_action=1`；
- planner audit 增加 query ID、active/available、source、start/end interval，并与 query table 逐步交叉核对；inactive arm 必须 NaN/-1/empty；
- raw manifest 保存 `raw_streams_npz_sha256` 与 `trace_source_sha256`；实际 manifest file hash 保存到 `manifest.sha256.json`，避免自引用哈希悖论；branch receipt 返回该 file hash；
- primary 26-D layout 保持 `controller_effective_setpoint_v1_layout_v2_1` 不变。

### Current/anchor

- `current_context_hash_v2` hash 完整 camera names/resolution/intrinsics/extrinsics/mount/near-far/renderer/settings；
- 强制实体 role/name/model/id/visual+collision asset hash/scale/body/mass/friction/collision/pose/velocity/sleep schema；
- model-visible 与 hidden-physical hashes 分开，明确 hidden physical 不可作为模型输入；full aggregate 同时保护物理等价；
- `physical_anchor_v2` 保存 dynamic actor pose/linear+angular velocity/sleep、facility pose、robot qpos/qvel/drive target/actual gripper qpos、physics config/source commit；
- pose 比较使用 position norm 与 sign-invariant quaternion angular error，独立 velocity tolerance。

### Root 四个 P0

- 新 `root_orchestrator_v1_1.py` 将 `audit_task_physical_feasibility`、freeze 和 post-freeze planner audit 分开；
- `CleanupUncertain` 立即终止整 root；
- 每场 scene 使用唯一 `scene_instance_id` 绑定 cleanup receipt，不再读取全局 last-cleanup；
- planned spec、program、task-tree input、prefix input、planner variant 均以 detached copy 传入并在返回/异常路径复核 hash；
- feasibility 前保存 provisional programs/task trees/prefix；
- finalizer 直接复核 branch current、anchor、actual executed-prefix bytes/steps/start/end anchors；
- raw 写入后立即记录 `raw_saved_verifier_pending`，verifier 抛异常仍保留 manifest/raw。

### F1–F4

- F1：actual prefix action SHA/step/start/end anchor；target 在 prefix command path 中不可见；neutral hold 只允许最低必要帧；
- F2：六个固定 planner variants 各用独立 fresh scene；真实 planner reset receipt；preplace terminal qpos 链到 release start qpos；
- F3：保存 initial/before-release `T_eef_actor` 与 drift；grasp slip、EEF tracking、systematic offset 分流；transient 与 final failure 分开；
- F4：Route1/Route2 各自 fresh planner scene；Route1 cleanup uncertainty 禁止 Route2；segment qpos chain；carry envelope 同时覆盖 common-X 和 gripper。

## Concrete real code

重点文件：

```text
controlled_multi_future/root_orchestrator_v1_1.py
controlled_multi_future/real_sapien_adapter_v1_1.py
controlled_multi_future/family_runners_v3_1.py
controlled_multi_future/family_repair_orchestrator_v1_1.py
controlled_multi_future/runtime_v3_1_contracts.py
controlled_multi_future/current_hasher.py
controlled_multi_future/anchor.py
controlled_multi_future/raw_writer.py
controlled_multi_future/probes/runtime_trace.py
controlled_multi_future/probes/a0_real_sapien_adapter_smoke.py
controlled_multi_future/probes/runtime_v3_1_root_runner.py
controlled_multi_future/probes/runtime_v3_1_family_repair_runner.py
controlled_multi_future/probes/runtime_v3_1_authorization.py
```

`RoboTwinRealSapienPilotRootAdapterV1_1` 是 concrete class，并延迟到 scene entry 才导入 SAPIEN。所有真实 CLI 必须读取并验证一个未来的、内容哈希匹配的 `cmf_runtime_v3_1_gpu_authorization_v1` receipt；当前不存在该 receipt，因此不能运行。

## CPU evidence

- Active tests：70/70 passed；
- Vault byte-equal snapshot tests：70/70 passed；
- 57 Python files compile passed；
- Current synthetic namespace：
  `数据构造/实现审计/probe_outputs/nonformal_root_pipeline_dry_run_runtime_v3_1_20260829_cpu4/`
- root receipt SHA-256：`8286b87be8e6b4116abc0517e60cbc01d5651fcf63071dd8396f632ce766a3e9`；
- freeze=1、task/physical scenes=3、planner scenes=3、rollout scenes=3、cleanup records=10；
- 三条 branch raw integrity 3/3、executed-prefix finalizer pass；
- 全部 `formal_data=false`、`stage0_data=false`、`synthetic=true`。

## 仍然明确未完成

1. A0 real-SAPIEN zero-action smoke 未运行；
2. concrete adapter/runner 未获真实 runtime validation；
3. F1 real red/green/blue 3/3 未运行；
4. F2 real beside 未运行；
5. F3 当前 runner 只覆盖 V→H release diagnosis，完整三个 programs 明确 incomplete/fail-closed；
6. F4 当前 runner 只覆盖 common-X route repair，A/B/C 和完整三个 programs 明确 incomplete/fail-closed；
7. budget 仍 proposed/unapproved/unfrozen；
8. Stage 0 仍禁止。

## 请 GPT 裁决

1. 四个 root P0 与 provisional/finalizer/raw-retention 修复是否充分？
2. manifest file hash 使用 sidecar 的自引用处理是否接受？
3. current/anchor 的 visible/hidden 分离与真实 camera/entity schema 是否足够？
4. concrete adapter 的 scene-bound cleanup、canonical settle、planner reset/chaining还有哪些 GPU 前 P0？
5. 是否可以只批准 A0（0 planner、0 action、4 scenes、600 s），仍不批准 family probes？
6. 如果 A0 通过，是否接受当前 F1/F2/F3/F4 finite envelopes作为后续分阶段非正式 probe proposal？
7. 是否同意继续保持 `BLOCKED_WITH_REASONS` 并禁止 Stage 0？

请不要把 synthetic pass 或 concrete class 的存在解释为真实 SAPIEN 可行性。任何 GPU 建议必须逐 Gate、有限、非正式，并与 Stage 0 authorization 分开。
