# Stage 0 readiness — runtime-v3_4_1 current

## BLOCKED_WITH_REASONS

CPU/code hardening 已通过 active/snapshot 各`461/461` tests 和各`151/151` Python compile，active/snapshot byte-equal。F1 targeted shared regression已3/3 accepted；F2 targeted的Entry/Safety通过但最终true-cavity/exclusive-inside失败，本v3_4_1不再开F2 full root；F3/F4尚待targeted GPU0 scopes。

当前 accepted nonformal pre-Stage0 roots 仍为1/4（仅历史F1）。Stage0 trajectory=0，Stage1=0，formal F1–F4=0，`H_reveal=null`，没有training/compression/π0.5。

只有当 F1 shared regression、F2 inside targeted + full root、F3 three-context targeted + full root、F4 exact corridor+A + B/C preflight + full root 全部通过，并且所有current/anchor/prefix/raw/verifier/cleanup/Guard回执完整时，才能生成 `STAGE0_USER_APPROVAL_REQUEST_RUNTIME_V3_4_1`。即使生成该请求，`stage0_authorized` 仍必须为false，等用户另行批准。
