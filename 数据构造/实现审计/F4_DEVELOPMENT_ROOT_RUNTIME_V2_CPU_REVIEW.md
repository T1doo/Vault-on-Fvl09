# F4 development-root Runtime V2 CPU review

日期：2026-09-04

结论：`PASS_READY_FOR_EXTERNAL_REVIEW`

F4 保持 `PHYSICALLY_QUALIFIED`，root 保持
`INFRASTRUCTURE_BLOCKED_BEFORE_BRANCH`。Runtime V2 的 CPU 基础设施修复现已完成，
但本文件不授权 GPU、scene、planner、physical 或 root execution。

## 最终冻结

- source freeze Vault HEAD: `9b4efa5691a746688c2516abb3d99b5659d66eb8`
- manifest contract: `64484a94d436e5c521975b8906c427965235865c278f16e7a935a63376f58bb9`
- Guard: `884ccd6c946991b95f8a92e2c7740bc83eb6e6a4d4ae09d0a047cd1f4f7d7702`
- runner: `e9217b437e360e0fdd2540420ff86b094c5ec4f8e59c1aebd37458aa1e89e175`
- lifecycle preflight source: `cc3c1db3b12a8e735d4c24e3afd7e3b195257a14bcad5430a9d4c7a9781c5c36`
- proposal manifest: `8afaf49a83aaaedc9473cd20866ad06e2b18e1f8adfcd1e6747baa401ce0a4f5`
- final lifecycle receipt: `3df1f4c21fec4c1b7f304c8a0f08351179f0eaf1dad2039e699be02547d3a3ba`

## 最终 CPU lifecycle

测试真实模拟了：

```text
all paths absent
→ PREPUBLICATION pass
→ GUARD_ENTRY pass
→ create guard/start/stdout/stderr/cache+9 subdirs
→ runner-entry subprocess
→ RUNNER_ENTRY pass
→ exact run_f4_development_r_pc_root dispatch selected
→ Run2/Run9/Run10–14/source/planner terminals resolved
→ stop before scene/GPU/planner/output
→ cleanup temporary paths
```

13 个负例全部 fail-closed，包括缺 guard/cache、错误 start receipt、已有 output、
错误 asset/candidate/program/budget/source/planner terminal、旧 third-reopen 字段和
runner preflight side effect。

Run10–Run14 五项具名回归全部通过；三个 source planner terminal 均为
`12 target construction + 30 chain = 42`，suffix aggregate=126，未来 root 总预算为
`10 + 126 = 136`。

## 失败历史未隐藏

1. 第一次 lifecycle 在 Run2 旧式 receipt self-hash 上停止；最终采用 exact file SHA、
   recorded receipt 和 5/5 content 三重绑定，并显式保留 historical self-hash=false。
2. 第二次抓到 proposal planned-scene SHA 的一位转录错误，未发布前纠正。
3. 第三次 precommit lifecycle 通过，但因 source-freeze commit 尚未更新，仅作为 draft 保留。
4. 第四次绑定新 source freeze 的最终 lifecycle 通过。

所有尝试均没有调用 `nvidia-smi`、创建 GPU context/scene/real output 或消费授权；
真实 proposal output/guard/cache 路径仍不存在。

## 外审边界

只有新的外审明确 supersede 旧 `CLOSED_NO_REOPEN_REQUESTED`，并绑定上述 Runtime、
proposal 和 lifecycle hashes 后，才可生成一个新的 approved manifest 并执行恰好一个
F4 development root。不得直接把当前 proposal 的三个 false 改为 true 后运行。
