# GPT review handoff：runtime-v3_3 GPU0–7 / F1 revision-2 CPU baseline

## 当前裁决

```text
BLOCKED_WITH_REASONS
stage0_authorized=false
accepted nonformal roots=0
Stage 0 / Stage 1 / formal trajectories=0
```

本轮没有启动Stage 0、训练、H-reveal、compression或π0.5。

## 新的真实证据

F1 revision-1已在physical GPU0受控运行并终止为`failed_planner`：

- task/physical feasibility 3/3；candidate freeze一次；
- canonical prefix 793 steps，action SHA=`22f8c7c2…`；三fresh replay的current/anchor/prefix-end一致；
- red/green各10/10 suffix segments planner通过；
- blue前4段通过，第5段`safe_vertical`到EEF z=1.02 m失败；
- branch suffix execution=0、recovery=0；
- 8/8 scene cleanup通过、orphan=0、Guard无timeout、GPU释放通过。

旧receipt记录planner=26。独立源码审计发现官方`choose_grasp_pose()`另有12次未被旧trace拦截的batch API calls，每批10个pose candidates；revision-1完整posthoc API-call口径为38/64。旧证据不改写；完整24-file manifest、ledger snapshot与failure report均已新增。

## F1 revision-2 唯一修复

保留同一planner-assisted top-down grasp、4 cm+4 cm lift、1.02 m安全高度、scene/seed/left arm/container/verifier。只把role-local高位raise改为三色统一的frozen cluster-center carry hub：

```text
8cm lift
→ carry_hub_low  [-0.11, 0.02, lift_z]
→ carry_hub_high [-0.11, 0.02, 1.02]
→ original above-box / preplace / release / retreat / rest
```

没有blue-specific条件。CPU swept-AABB evidence无明显hard blocker；真实路径仍须CuRobo 3/3验证。F1只剩一次revision-2，失败后terminal，无revision-3。

## Planner与root fail-closed加固

- official grasp-target batch calls逐次记录：contact point、batch size=10、ordered goal hash、10 statuses、selected index、start qpos、reset与wrapper restoration；
- batch API call与内部pose slots分账；
- canonical/root/F4-staged均要求live planner delta等于receipt；
- actual count还必须不超过source-bound envelope：F1=46、F2=35、F3=55、F4=138；
- suffix失败也写family comparative Gate；future roots写`root_terminal` event及event-log hash；
- active source与snapshot source SHA均为`40e2ef209ba407e44cdf952637d4725b57daa8194f9cde0cd7ab6d6b2cfaf037`。

## GPU0–7并行政策

用户最新明确授权physical GPU0–7任一实时空闲卡，并允许不同卡的独立family jobs并行。旧GPU0-only receipts保持其历史有效性；新scope使用新parent authorization和budget v1.1：

```text
budget receipt SHA = 68cee0949ccb6d87bef5255560bf32737d0d79dc803dfd92ac71d1098cad5d2c
```

新Guard提供：

- per-physical-GPU `flock` lease，防止两job同时抢同一卡；
- physical index/UUID两次fresh-idle检查；
- 每job独立HOME/TMP/Conda/Pip/Torch/HF/CUDA/Triton/MPL/Numba caches；
- child侧复验lease与全部cache env；
- Popen信号mask、PDEATHSIG、PID/PGID running receipt、ownership-scoped process-group cleanup；
- atomic guard/child receipts、stdout/stderr与child receipt hash；
- post-GPU release和post-source-lock复核；cleanup uncertainty拥有最高终态优先级。

## CPU证据

```text
active tests   = 256/256 passed
snapshot tests = 256/256 passed
source diff    = byte-equal
tests diff     = byte-equal
official HEAD  = c3ddfa8b97d5519efa828b075999bd0006778e5e
official tracked status = clean
```

多代理只读P0 sweep对最新字节未发现剩余确定性P0。本baseline之后尚未运行GPU。

## 下一步（发布后）

分别签发fresh one-shot bundle；只在不同卡各自fresh-idle时并行：

1. F1 revision-2（最后一次）；
2. F2 revision-1；
3. F3 revision-1；
4. F4 staged A/B/C/AB + revision-1 root。

每个scope有独立namespace、authorization、family ledger、GPU lease、process tree与cleanup receipt。四个accepted roots全部形成以前，不创建Stage 0 execution package。

## 首选审阅入口

- `F1_STRICT_PREFIX_ROOT_RUNTIME_V3_3_REVISION1_FAILURE_REPORT_20260829.*`
- `F1_STRICT_PREFIX_ROOT_RUNTIME_V3_3_REVISION1_EVIDENCE_MANIFEST_20260829.json`
- `F1_STRICT_PREFIX_ROOT_RUNTIME_V3_3_REVISION1_LEDGER_SNAPSHOT_20260829.json`
- `F1_UNIFORM_CARRY_HUB_REVISION2_IMPACT_REVIEW_V1_20260829.*`
- `USER_AUTHORIZATION_RUNTIME_V3_3_PRE_STAGE0_WORK_GPU0_7_20260829.*`
- `PRE_STAGE0_RUNTIME_V3_3_SCOPE_BUDGET_V1_1.*`
- `f1_f4_implementation_registry_v3_3_cpu_current.*`
- `stage0_readiness_report_runtime_v3_3_cpu_current.*`
- `代码审阅快照/`
- `正式数据构造日志.md` sections 145–147
