# F4 development r_pc root impact review V1

日期：2026-09-03  
范围：最多一个 post-qualification development root；非 Stage 0、非 Stage 1、非 formal

## 1. 前置证据

`RUN9_MICRO_GATE_TERMINAL_V1.json` 已证明同一 r01 的 `ABC/ACB/BAC` 三条真实完整程序 3/3 通过，same-current、same-anchor 与 final-state-equivalence 全部通过；payload=`3bf30f95593e6e5a1534cb271bfa0e167cc685326008e3e720e9abf68275fb5c`。

该 Gate 只解锁最多一个 F4 development `r_pc` root。F2/F3 不因此解锁，Stage 1/formal/training 不因此授权。

## 2. 发现的 production/root 差异

现有通用 F4 strict-prefix controller 固定右臂执行 common-X 和全部 A/B/C suffix；Run9 真正通过的 r01 则固定为：

- canonical common-X prefix：右臂；
- `ABC/ACB/BAC` program suffix：左臂。

直接调用旧 root adapter 会静默切回未由 Run9 资格化的全右臂路线，因此禁止。新实现保留 `right-prefix → left-suffix` 的固定 arm schedule，三分支完全一致；后续 `r_inv_path/r_inv_motion` 也必须保持该 schedule，不能用换臂充当 invariance。

## 3. 最小实现变化

复用现有 `RealSapienStrictPrefixRootOrchestratorV1_2`，不改其生命周期、候选冻结、prefix artifact、raw writer、video、finalizer 或阈值。新增/扩展内容只有：

1. `f4_full_program_physical_v1.py` 增加从真实 replay-end state 规划左臂三角色 suffix、冻结 control artifact、在 branch scene 无 planner 重放 suffix，并输出 250 Hz raw-first streams；
2. `real_sapien_adapter_f4_qualified_root_v1.py` 只覆盖 F4 suffix planning/execution/verify，prefix generation/replay、scene/current/anchor、task feasibility 和 family comparative Gate 均沿用原实现；
3. run-layer 增加 `ONE_F4_DEVELOPMENT_R_PC_ROOT_V1` mode，并要求 Run9 template terminal、Run2 source planner envelopes、r01 candidate/spec 全部 hash-bound。

Suffix verifier在Run9 final checks之上增加逐角色 selected-gripper contact continuity/actor identity、未完成对象 preservation、已完成 slot preservation；不降低任何既有阈值。

## 4. Root 合同

Root orchestrator必须产生并验证：

- reference current 只保存一次，所有分支通过 SHA reference；
- one candidate universe / one task tree / one canonical prefix artifact；
- canonical prefix 只规划/真实生成一次，三次 suffix preflight 与三条 branch 均精确 replay；
- 所有三条 suffix planner在任何 branch execution前通过；
- `ABC/ACB/BAC` 各一个 fresh branch、各一条真实 `r_pc`、raw-first 250 Hz 与 MP4；
- branch verifier 3/3、final-state equivalence、action divergence、cleanup/orphan/finalizer 全过；
- root atomic：任一项失败则 root incomplete，成功部分不进入 development accepted count。

## 5. 预算与停止

- root invocation：最多 1；automatic retry=0；第二个 F4 root 禁止；
- planner：canonical prefix 10 + 三个 suffix 各 30，aggregate maximum=100 queries；
- fresh scene upper bound=11（pristine 1、task feasibility 3、prefix reference 1、suffix preflight 3、branch 3）；
- robot-action scenes upper bound=7（prefix reference 1、preflight prefix replay 3、branch prefix+suffix 3）；
- raw/video branches maximum=3；accepted formal trajectories=0；
- finite timeout=28800 s；任何 infrastructure/planner/prefix/branch/finalizer terminal 都停止，不 retry。

## 6. CPU/static validation

- 309 controlled Python files与更新后的run-layer runner AST pass；
- active/review 两个新增或修改的 F4 files byte-equal；
- Run9 三个 immutable full-program specs 被 adapter 精确接受，并共享 planned scene SHA=`99240a809efab02bb1a6afd0e47921198451dce43845c6c3e15a72307dfc00f1`；
- provisional programs精确为 `F4-ABC/F4-ACB/F4-BAC`，candidate freeze dry construction SHA=`812a90425662352ccb4f0402549aea9a879ddf17a8d189e0464a772d021bfed6`；
- 未运行 fake-heavy suite，未初始化 GPU。

Controlled source SHA=`a7fbc996760136017bbf757d05d5af4e6aecc54a5b019f4abf5d10ba86666002`。

## 7. Run10 integration evidence 与唯一 replacement

Run10 在 candidate freeze、prefix planning 和 branch execution 之前终止。旧 F4 task-feasibility audit 固定要求 slot center distance ≥0.10 m；r01 相邻 slot center distance 为0.09 m，但 block width=0.044 m，真实表面间隙=0.046 m，且 Run9 已真实完成三条程序。该旧 center-distance heuristic 与 r01 的 versioned corridor certificate/真实物理证据不兼容。

Replacement 只在 qualified-root adapter 内将旧0.10 m check降为diagnostic，并要求：原有非slot checks全过、r01 candidate self-hashed construction valid、no online fallback、positive terminal surface clearance、runtime static slot pose相对candidate spec的position/orientation误差分别≤1 µm/1 µrad。没有改变slot/final-state verifier、program、candidate、物理阈值或执行器。Run10 branch/raw/video/planner/action消费均为0，因此允许一个同root、同预算的新namespace integration replacement；若同层再次失败则停止。
