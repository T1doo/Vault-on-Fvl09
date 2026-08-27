# F1–F4 repair probe design v1

CPU design 已完成，GPU execution 尚未开始。所有 probe 均为 `formal_data=false / stage0_data=false`，旧 failure receipt/trace 不覆盖。

- F1 固定 red RGB block、left arm、`062_plasticbox/base3` 与原 layout：先跑官方 left-arm 对应的 `fp1`，失败后才跑明确 interior target；每 variant 一次执行，place 段最多 2 个 planner queries。
- F2 固定 `071_can/base1` 与 left arm：stand 周围只按顺序测试 north sector 与 northeast sector；两者均失败后才允许另建 pot audit，且不得换 can/arm。
- F3 固定 `001_bottle/base13`、left arm、table-z/table-x 与 original pad：先跑 pad-center world-z 分段 return，失败后才跑 bottle functional-point 方案；return 段最多 2 个新 planner queries，release 后使用已规划路径反向撤离并回到 central/rest。
- F4 严格按 `common → A → B → C → common_ab → ABC → ACB → BAC`，前一步失败即停止；本轮不执行 strict array/block reorder。

精确静态尺寸、functional points、sector 坐标与有限预算见同名 JSON。
