# F3 Grasp Physical Run3 Result

终态：`BOUNDED_GRASP_SEARCH_EXHAUSTED_REQUIRES_ASSET_REDESIGN`

- r01、r02：pre-shared-V Gate 失败，包含 grasp translation/orientation drift、selected contact continuity 和 bottle off-support failure。
- r03、r04：`f3_prefix_pregrasp` planner control failure。
- 4/4 candidates 各执行一次真实 physical qualification；stable grasp=null。
- 因无 stable grasp，不运行 3-fresh-scene confirmation，也不运行 VVHH/VHVH/VHHV development root。
- 全部 Guard cleanup/source/post-release 通过，orphan=0。

Machine result：`F3_GRASP_PHYSICAL_RUN3_RESULT.json`，payload `7d6fc66bcb8177d20fa3141d453d11c7b3dab7a55e03886ca0130d55ee589f06`。
