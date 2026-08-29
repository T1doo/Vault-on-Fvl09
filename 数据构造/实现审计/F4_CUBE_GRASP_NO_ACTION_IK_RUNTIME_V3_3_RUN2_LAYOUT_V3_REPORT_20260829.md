# F4 no-action IK：layout-v3 run2

Layout-v3把A/B/C统一移到right x-band `0.18/0.29/0.40`，但三者在y=`0.175`仍全部首段pregrasp失败。Planner各1 query、execution=0；四scene cleanup、budget、Guard post-release和独立GPU0 postcheck全部安全。

这排除了“仅x太靠左”作为完整解释。历史common-X成功点为actor y=`0.10`、pregrasp y≈`0.079`；layout-v3三对象pregrasp y≈`0.154`。最后一个统一repair只调整整行y-band，不改orientation、pregrasp distance、arm、objects、tray、programs或verifier。

若最终共同layout仍不能让A/B/C 3/3通过no-action IK，则F4在runtime-v3_3终止，不进入staged/full root。
