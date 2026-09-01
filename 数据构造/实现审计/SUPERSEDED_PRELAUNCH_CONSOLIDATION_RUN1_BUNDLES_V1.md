# Superseded Prelaunch Consolidation Run1 Bundles V1

状态：`UNCONSUMED_SUPERSEDED_DO_NOT_RUN`

CPU freeze baseline 已成功发布到真实 Vault HEAD：

`c25467ee6e486a4946b643b0fb10f33051084118`

第一次签发 8 个 consolidation run1 bundles 时，调用方把短 SHA `c25467e` 手工补成了错误的 40 位值：

`c25467e6e86ad9306ff10d2e2865278979cc9754`

因此所有 run1 authorization 即使通过格式/self-hash 检查，也没有绑定真实 published HEAD，全部禁止运行。逐项只读审计确认：8/8 未消费、Guard 不存在、output 不存在、job cache 不存在、GPU execution=0、trajectory=0。

Machine evidence：`SUPERSEDED_PRELAUNCH_CONSOLIDATION_RUN1_BUNDLES_V1.json`，payload `2b0c25ae714082ede92e28dfbe007b8cdb6c64fef0ca2f8c1c3029fe2aa945a1`。

签发器现已增加硬 Gate：传入 commit 必须等于 Vault 本地 `HEAD`，且本地 `HEAD` 必须等于 `origin/main`。修复后 active/snapshot full suite 均为 `666/666`；后续只允许重新发布后的 run2 identity。
