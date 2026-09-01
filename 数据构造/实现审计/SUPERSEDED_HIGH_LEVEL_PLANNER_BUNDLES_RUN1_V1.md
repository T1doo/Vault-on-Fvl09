# High-Level planner run1 bundles 封存

28 个 run1 authorization 全部标记为 `UNCONSUMED_SUPERSEDED_DO_NOT_RUN`。

启动前审计发现：新的 High-Level authorization 自身验证链已实现，但通用 `gpu_guard_v2_4.py` 尚未路由该 implementation version 的 load/consume/validate。因此 run1 在任何 GPU 扫描或启动前被封存。

- Authorization：28（F2=12、F3=8、F4=8）
- Guard：0
- Consumption：0
- Output namespace：0
- GPU job：0
- 旧 source SHA：`158a07be17bf863bdc3c8db0966a8015ea229763de5b10b10a925bd519e6790c`
- 修复后 source SHA：`c7b6357d6dc8d0ec9630b4f3569c4d0218aca972e0519443c49591fbb900bb61`
- Authorization manifest SHA：`608e4c6bb2c2d3bef94ca2d7d49461e8b2bf23689f32fcdadc81bd7d445590bf`
- Artifact payload SHA：`8f270127a2cdf5ca407ef80c5c29fac22bd9d542210c1fefe44db4339be8563c`

修复只增加 High-Level Guard 路由，不改 F2/F3/F4 候选、planner/physical 语义、budget、阈值或分母。Active/review-snapshot 完整suite均为 703/703。后续必须使用新source-hash绑定的run2 bundles。
