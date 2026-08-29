# controlled_multi_future_runtime_v3_1 implementation proposal

状态：`cpu_static_hardened_v5_a0_approval_ready_pending_user_review`。

```yaml
design_version: controlled_multi_future_f1_f4_v1_2
implementation_version: controlled_multi_future_runtime_v3_1
root_orchestrator: real_sapien_pilot_root_orchestrator_v1_1
a0_orchestrator: A0CurrentAnchorOrchestratorV1_2
a0_activity_audit: cmf_a0_activity_audit_v2
real_adapter: RoboTwinRealSapienPilotRootAdapterV1_2
gpu_authorization: cmf_runtime_v3_1_gpu_authorization_v1_1
gpu_guard: cmf_gpu_guard_v2_1
current_hash: current_context_hash_v2
physical_anchor: physical_anchor_v2
raw_schema: cmf_raw_attempt_v2_1_1
primary_action_layout: controller_effective_setpoint_v1_layout_v2_1
gpu_probe_authorized: false
stage0_authorized: false
formal_data: false
stage0_data: false
```

## 本轮实现

- task/physical feasibility 与 planner solvability 分账；candidate universe 在前者通过后 freeze 一次；
- 每场 scene 使用唯一 `scene_instance_id` 与绑定 cleanup receipt，cleanup/orphan 不确定立即停止；
- planned spec、program、planner variant 在每次 adapter call 前后做 hash 不可变性检查；
- feasibility 前保存 provisional programs/task trees/prefix；
- finalizer 独立重查 branch current、anchor 和实际 executed-prefix bytes/steps/start/end anchor；
- raw 写入后、verifier 前先保存 manifest 与 branch partial receipt；
- raw 增加真实 scene timestep、planner query ID/active interval/source 和 NPZ/manifest/trace integrity hashes；
- current hash 分离 model-visible 与 hidden physical components，实际 camera config 与实体 schema 均强制；
- physical anchor 使用 sign-invariant quaternion angular error，并保存 actor velocity/sleep state、drive targets 与 physics config；
- 实现 lazy-import concrete RoboTwin adapter、F1 root runner、F2/F3/F4 repair runner、A0 zero-action entry point 与内容哈希授权 receipt Gate。

## Family 当前边界

| Family | 当前 runner scope | 完整 root 状态 |
| --- | --- | --- |
| F1 | red/green/blue 三分支、实际相同 prefix、3/3 root | 已静态实现，未运行 |
| F2 | 固定同 can/left/stand；六个 fresh-scene planner variants；chained preplace→release；beside execution | 已静态实现，未运行 |
| F3 | V→H realized diagnosis、grasp-transform drift、release samples、return | 完整 VVHH/VHVH/VHHV 明确未运行，root verifier fail-closed |
| F4 | common-X Route1/Route2 fresh-scene repair、combined object/gripper carry envelope | A/B/C 与 ABC/ACB/BAC 明确未运行，root verifier fail-closed |

## GPU-preflight hardening v3

- F1 actual prefix 在边界前不读取 target role 或 target-specific execution spec；root 从 raw actions 独立重算 prefix hash、逐步 suffix hashes 与首次分叉点；
- F1/F2/F3/F4 repair verifier 补齐 staged noninterference、support/stability、release/rest/gripper/EEF stationarity；
- F3 samples 强制速度、pad contact normal/impulse、selected-gripper contact、actual gripper qpos；
- current exact hash 只覆盖 model-visible current + reconstruction spec；hidden physical state 交给 `physical_anchor_v2` 容差比较，entity asset/physics registry 在 anchor 中精确锁定；
- chained planner 将 6-D arm terminal 合并回完整 articulation qpos；
- F4 gripper envelope 从真实 selected-link poses 推导，不再硬编码；
- real trace source 单独落盘并绑定 SHA；manifest payload 会重新计算验证；
- GPU child 必须由当前 guard PID 在 60 秒内 fresh-idle precheck 后启动，且 top-level receipt 可被 guard 原子 postcheck；scene/outer orphan 分开记录并合计。
- F3 conditional correction 已实现为独立状态机：1 次 diagnosis；仅 stable grasp + normal EEF tracking + systematic pre-release offset 可生成内容哈希 correction spec；diagnosis/correction fresh current 与 anchor再次等价后最多执行 1 次；grasp slip、post-release physics、cleanup/current mismatch 均禁止或终止 correction。

## GPU-preflight hardening v4

以下为保留的 V4 历史实现；已由 V5 activity monitor／orchestrator／adapter／authorization／guard supersede，不再是 current execution entry。

- A0 从 GPU CLI 中抽离为 adapter-agnostic `A0CurrentAnchorOrchestratorV1_1`；CLI 只负责内容哈希授权、atomic GPU guard 与真实 adapter 装配；
- A0 固定构造 `A0_pristine + A0_fresh_1/2/3` 四个唯一 scene，逐场保存 current、anchor、activity audit 与 scene-bound cleanup receipt；
- fresh current mismatch、physical anchor mismatch、planned spec mutation、cleanup uncertainty 均立即终止，不会继续后续 scene；
- 每场必须显式证明 `planner_query_count=0`、`planner_query_record_count=0`、`action_execution_count=0`，并把 canonical setup settle 与 controlled action 分开；
- 新增五项 A0 synthetic tests，分别覆盖四场景通过、current mismatch、anchor mismatch、cleanup uncertainty 与 planner activity violation。

## GPU-preflight hardening v5

- `A0PostSetupActivityMonitorV2` 在 `setup_demo + 60-step canonical settle` 完成后才启动；实例级 wrapper 独立覆盖 task control、robot planner、direct drive、renderer 与 physics step，不再用“trace 不存在”推断 action=0；
- v2 activity receipt绑定 scene/phase/monitor boundary/setup summary、独立 planner/control records、physics/renderer delta、wrapper install/restore 与内容 hash；任何非零 planner/control/physics 或 instrumentation 异常立即失败；
- `A0CurrentAnchorOrchestratorV1_2` 每 scene 分离保存 current/anchor/activity/cleanup/artifact hashes，top receipt只引用 hash；current/anchor mismatch 另存 component diagnostics，但不放宽正式 Gate；
- `RoboTwinSceneContextV1_2` 在 setup/settle 后安装 monitor，capture 后停止，cleanup 再保证恢复；真实 timestep必须为 0.004；
- procedural block/pad/marker/slot 的尺寸、颜色、collision/visual-only、material source与 creation API进入 asset/physics hash；camera 与 friction metadata明确 runtime/declared/unavailable source；
- one-shot authorization v1_1绑定 scope/family/seed/spec、代码 hash、budget、timeout、output、command与 allowed GPU policy；guard在 child 前以 `O_CREAT|O_EXCL` 消费一次，失败也不复用；
- guard v2_1绑定 authorization/consumption/budget/source/command/output/GPU/PID，并继续执行 fresh-idle、timeout、child receipt、orphan和 post-release；
- 六个未来 probe scope 都有机器预算 validator，目前只有 A0 requestable；历史 runtime-v2/scene-inspection/environment-certification/guard CLI 已 fail-closed；
- 已生成 `A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.md/json`，状态保持 `approved=false / gpu_probe_authorized=false`。

CPU current：active/snapshot 131/131 tests passed，76 Python files compile passed；root-cpu10 synthetic dry-run accepted。Import audit未加载 SAPIEN/Torch/CUDA。它们不证明真实 SAPIEN，也不表示 A0 已运行。

当前 `a0_user_approval_readiness=READY_FOR_USER_REVIEW_BEFORE_A0`。任何 GPU 运行仍必须由用户单独批准并生成最终 `approved=true` authorization receipt；Stage 0 明确禁止。
