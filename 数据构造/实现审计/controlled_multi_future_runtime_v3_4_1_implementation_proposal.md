# controlled_multi_future_runtime_v3_4_1 implementation proposal

当前状态：`cpu_source_frozen_publication_pending`。

本版是唯一的 one-shot postmortem hardening，不开始 `v3_4_2`或 revision 链。已完成：

- 统一 planner/execution/primary-failure/cleanup/evidence schema；
- F1 以4+11而非11计数；
- F2 PreloadEntryEvidenceV11 与原 v10 safety/final Gate 分责；
- F3 三个canonical-ID fresh-scene diagnostic contexts；
- F4 exact variable-length corridor、preplanner hash、joint-limit evidence、A-only与B/C planner-only Gate；
- authorization、single-use consumption、Guard、source/budget binding 和 guarded scope runner。

Active与byte-equal Vault snapshot CPU suites均=`461/461 passed`，两边151个 Python 文件 compile pass，active/snapshot diff为零。Source SHA=`81c8603699c2fa086f524cb313e17aca205f00a575e7cc92588de6576c120ffc`，tests SHA=`47c32b1767eb91a5a98a37a5d8658592504e69f8487a60950d039dd1f6e2fbf7`，budget receipt SHA=`f671f8f9e5e498a43dc7bf77dcd1dae921878eddcecd3f6cb71bfc662d342bb9`。

按 fvl05 最新 workspace 规则，本版新 authorization 只能绑定 physical GPU0；四个targeted scopes必须串行，每项启动前重新检查空闲，不得使用GPU1–7。

本 proposal 不授权 Stage0、Stage1、formal collection、training、H-reveal、compression 或 π0.5。
