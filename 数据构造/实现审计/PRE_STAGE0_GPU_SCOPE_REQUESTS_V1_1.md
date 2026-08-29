# Pre-Stage-0 GPU Scope Requests V1.1

```yaml
status: terminal_blocked_A0_budget_exhausted
implementation_revision: runtime_v3_1_cpu_hardening_v5_1
a0_repair_revision: a0_sleep_state_property_compat_v1
reviewed_content_commit: 02e00f9e3f753586eb16d7369bb48e75049ce05e
parent_user_authorization_sha256: 8b93677781037fe172cd83c55e5ff45f731230e816b9ba60f38f04a49317cd83
scope_requests_bundle_sha256: fcf65041425e39c110202288120bd358bea926f05ff3b538a62fdd9c2be4d9d6
formal_data: false
stage0_data: false
stage0_authorized: false
```

本包 supersede V1 作为 current request入口。V1、A0 run1 authorization/consumption/guard/partial output和失败证据均保持不可变。

A0 run2 是总授权允许的第二次、也是最后一次 A0 execution。它只修复SAPIEN `is_sleeping`在fvl05上为bool property的问题；same-current、anchor、zero planner/control/physics、cleanup、orphan和GPU release Gate均未放宽。A0 run2若仍失败，不再运行第三次。

Current request SHA：

- A0 run2：`9046251ed180781fbd38e9e0a5dfe5bf1b2c5e1abfb1538eb9799cba9f293fc0`
- F1：`bb014f33def51db554b17ec6eaca8b741a8fa5d50262ad7a07c05253d12916bf`
- F2：`51337ebf1be92c36513d45be1fd3a6c0bc00c432241ee5a26a81c8a7a626aafd`
- F3：`8ec777db36ed0a717963b8e674237af7e40538d64ed2c3cc82578db55ff6b0fe`
- F4：`c537e62ae0adf01b3b92c3a8276a71401b2d7a5360d44280f3f444fda662053e`
- Real root integration：`e3873ee091187388e7c7d3225965dcf761b63db88dfaf6069eddd560b898d6b3`

逐request payload位于`scope_requests/runtime_v3_1_v5_1_r1/`。每个后续scope的硬前置是A0 run2通过；仍需独立source lock、≤1小时one-shot authorization和即时fresh-idle guard。

## Terminal update

A0 run2 已执行并因 `0.004000000189989805` 被旧 exact-float validator 拒绝；同时发现A0未初始化native planner ledger。两次获准A0 execution均已消费，故不再运行第三次。F1–F4与real-root request虽然保留为预注册证据，但A0前置未通过且postmortem active source已变化，当前全部不可launch。后续若要复核CPU修复，需要新的用户预算和全新request/source-lock/authorization namespace。
