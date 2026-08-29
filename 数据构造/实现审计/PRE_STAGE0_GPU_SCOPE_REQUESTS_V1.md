# Pre-Stage-0 GPU Scope Requests V1

```yaml
implementation_revision: runtime_v3_1_cpu_hardening_v5_1
reviewed_content_commit: 66451020575b54e90a4a06d4dd86cf783ea172d5
parent_user_authorization_sha256: 8b93677781037fe172cd83c55e5ff45f731230e816b9ba60f38f04a49317cd83
status: superseded_after_A0_run1_versioned_source_repair
scope_requests_bundle_sha256: 7712bdec5d96789f03bc78dcb343390d6a9dc2844fa16b8a982cf4b214ea0098
formal_data: false
stage0_data: false
stage0_authorized: false
```

本包冻结六个用户已批准的 pre-Stage-0 nonformal scopes。每个 request 都绑定 exact family、seed、planned spec、content/source/budget hashes、child command、output namespace、GPU0–7 fresh-idle policy和单次 invocation。运行时仍须先生成并验证 family-specific launch-time source lock，再从 frozen request 生成有效期不超过一小时的 `approved=true` one-shot authorization；guard fresh-idle admission 通过后才原子消费。

> [!warning] 历史 bundle
> A0 run1 暴露 fvl05 SAPIEN `is_sleeping` bool-property compatibility bug后，active source发生versioned repair。本bundle中未消费的request因source binding变化自动失效；A0 run1 request/auth/source-lock/consumption/evidence保持不可变。Current request入口将由`PRE_STAGE0_GPU_SCOPE_REQUESTS_V1_1`替代。

| Scope | 运行内容 | 总 timeout | Request SHA |
|---|---|---:|---|
| A0 | F1 seed 20260829；1 pristine + 3 fresh；zero planner/control/physics | 600 s | `e62236fae39dfcaaed1405ff47e9153b81815b85d9050474abf67366fbce10bb` |
| F1 | red/green/blue 真实 fresh-scene 三分支 root | 3600 s | `4ff361c648c1f40f65f1800da25905d5006cd85764dbc6aa4209f36f4f0306fd` |
| F2 | six-pose workspace/chained preflight + inside/on/beside 三分支 root | 4800 s | `b8cde99e473a2bfac05d0123c19287c129107604b472f91f8d2f498563dde17c` |
| F3 | V→H release diagnosis/conditional repair Gate + VVHH/VHVH/VHHV root | 9000 s | `051e9d62ae782249b0d359debbaad8cd4aae86b1f5fb401e2226dd07712f4887` |
| F4 | common-X Route Gate + ABC/ACB/BAC root/block/noninterference verifier | 20400 s | `b1e5bf5a742861b5538bb2daeba9201cebf8a47f2643d417a18f26ef456a8205` |
| real root integration | 独立 F1 real-SAPIEN root pipeline integration | 3600 s | `1586e14ede7082aa5bb0cfee849f3d64f795be11c9b81ac8f21f7c6ad6bb9ac5` |

实际逐 request payload 位于 `scope_requests/runtime_v3_1_v5_1/`。A0 是第一个运行 Gate；A0 未通过时不启动后续 family scopes。F1–F4 或 cleanup/GPU safety 任一 terminal blocker 按 frozen stop line 处理，不自动重试。

本包不授权正式 Stage 0、Stage 1、正式采集、训练、`H_reveal`、compression或π0.5。
