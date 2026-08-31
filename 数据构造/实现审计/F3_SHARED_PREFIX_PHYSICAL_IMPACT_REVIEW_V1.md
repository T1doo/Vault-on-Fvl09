# F3 shared-prefix physical impact review v1

## 结论

Stage 0 partial trace把失败定位在所有program共用的close阶段，而不是V/H、suffix或verifier：`selected_gripper_contact`只在step 897–1031为真，step 1032首次丢失且之后未恢复；post-close settle结束step 1462时已经没有抓持。随后相对抓取平移在step 1466首次超过5 mm，旋转在step 1478首次超过50 mrad。

最终50帧（step 2750–2799）瓶子每帧仍与pad/table存在接触；EEF线速度在2766–2767超过0.01 m/s，角速度从2750持续超0.05 rad/s至2795。现有pre-V physical Gate拒绝该prefix是正确行为，门限不应放宽。

## 唯一共享修复冻结

冻结`f3_contact_preserving_partial_close_v11`：三个program统一保留`001_bottle/base13`、left arm、official contact0/candidate0与post-close 250帧，只把normalized close target从`0.0`改为`0.35`。静态drive target预计为`0.01575 m`，比Stage 0最后仍有接触的`0.0125499032 m`留出`0.0032000968 m`余量。

这是由旧trace提出的待证伪诊断假设，不是物理通过证据。禁止program-specific grasp、在线挑成功pose、fallback、retry或recovery；V/H、program、shared first V、release/return以及全部Gate/verifier阈值不变。

## 唯一允许的诊断

最多运行一次`same immutable canonical prefix × 3 fresh scenes × no suffix`：三scene必须复放完全相同的prefix action bytes并包含shared first V；suffix planner调用数必须为0，不执行suffix或release。每scene都必须通过same-current/anchor、prefix hash、持续抓持、5 mm/50 mrad抓取稳定、free-space无pad/table接触、shared-V realized motion、prefix-end stationarity与cleanup/orphan检查。

只有3/3全部通过，才可另行冻结并运行最多一个post-Stage-0 F3 development root。任何一项失败都终止本次F3开发波次，不进行第二次diagnostic或现场hotfix。此review和后续diagnostic均不修改Stage 0 seal、不增加accepted root、不授权Stage 1/formal/training/H-reveal/compression/π0.5。

机器可读证据与精确数值见`F3_SHARED_PREFIX_PHYSICAL_IMPACT_REVIEW_V1.json`。
