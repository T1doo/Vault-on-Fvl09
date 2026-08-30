# runtime-v3_4_1 CPU/source-freeze handoff

## 结论

`controlled_multi_future_runtime_v3_4_1` 已完成唯一的 CPU source freeze，但还没有运行新GPU/SAPIEN probe，所以当前仍是 `BLOCKED_WITH_REASONS`，不批准Stage0。

## 机器闭包

- locked parent Vault HEAD: `4c60f5515abfa8642237b45613d3724e509f843e`
- design: `controlled_multi_future_f1_f4_v1_2`
- implementation: `controlled_multi_future_runtime_v3_4_1`
- source SHA: `81c8603699c2fa086f524cb313e17aca205f00a575e7cc92588de6576c120ffc`
- tests SHA: `47c32b1767eb91a5a98a37a5d8658592504e69f8487a60950d039dd1f6e2fbf7`
- budget receipt SHA: `f671f8f9e5e498a43dc7bf77dcd1dae921878eddcecd3f6cb71bfc662d342bb9`
- parent authorization SHA: `b23fee6d86a35f8666ebbc4ad83229e550ba849b983e5a92a35c674450ca93f6`
- active tests: `461/461 passed`
- snapshot tests: `461/461 passed`
- active/snapshot compile: `151/151` each
- active/snapshot byte-equal: true
- official tracked baseline: `c3ddfa8b97d5519efa828b075999bd0006778e5e`，tracked files unchanged

## 四个family的实际修复

- F1：将每分支4个target-construction query与11个executable control-chain query分账，scope total=15，不改scene/target/program/verifier。
- F2：新增PreloadEntryEvidenceV11，旧0.02/0.05只作diagnostic；partial-open后仍使用未改的v10 safety Gate，full-open后exactly250帧再使用未改的v10 final Gate。
- F3：删除D3 alias路径，保持canonical F3 IDs、3 fresh scenes、same prefix、shared V + first suffix event，停在release之前，nonroot finalizer不调generic final-equivalence。
- F4：完整应用每candidate的variable-length segment IDs/pose hash，每成功segment保存terminal qpos/joint margin，固定c1→c4、首个pass即停，然后最多一次A-only、B/C planner-only、条件full root。

## GPU权限更正

当前fvl05 `AGENTS.md` 的最新硬规则是physical GPU0-only，因此本v3_4_1 parent authorization、budget、bundle和validator都只允许`[0]`，四个targeted scopes串行。这只改变调度权限，不改科学设计。

## 下一步

发布本CPU freeze并恢复clean `HEAD=origin/main`后，才可以签发和消费四个single-use targeted bundles。每个family失败即停止该family；只有targeted pass才签发条件full root。任何source修改会终止v3_4_1。

本轮没有Stage0/Stage1/formal data、training、H-reveal、compression或π0.5。
