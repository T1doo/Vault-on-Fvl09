# controlled_multi_future_runtime_v3_4 implementation proposal

当前状态：`cpu_source_frozen_gpu_targeted_pending`。

唯一执行顺序为：旧证据forensics → 每family一个假设 → CPU全测 → source/snapshot冻结 → F1回归与F2/F3/F4 targeted Gate按独立空闲GPU并行 → 仅passing family运行一次完整nonformal root → readiness更新并停止。

Source SHA=`1cadd3e28af56f56c32e8fe363fbeb3c2f3397ff196a63c6bd115285aa85b316`；budget SHA=`99d017cc32fc07bf055ca18efbd2b943a62e385750c78820dd0437d77f393bfa`。

本proposal不授权Stage0、Stage1、formal collection、训练、H-reveal、compression或π0.5。
