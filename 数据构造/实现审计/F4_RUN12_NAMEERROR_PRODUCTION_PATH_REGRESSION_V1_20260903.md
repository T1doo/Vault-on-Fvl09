# F4 Run12 NameError production-path regression V1

日期：2026-09-03  
状态：`PASS_CPU_PRODUCTION_PATH`

- 新回归文件：`tests/controlled_multi_future/test_f4_qualified_root_production_path_regression_v1.py`
- 文件 SHA-256：`7a4527c825027e02e457d259a3ba328ed19b4b7f17fc3d5362cbff33797b43b2`
- 直接调用：`plan_f4_full_program_suffix_from_replayed_prefix_v1`
- 覆盖的原失败路径：12 target-construction queries + 30 chain queries = 42，然后进入 `_cache_preplanned_suffix_controls` receipt packaging。
- 断言：`query_count=42`、`chain_query_count=30`、receipt packaging 实际被调用，不再触发 `total_before` NameError。

执行记录：

1. `python -m unittest tests.controlled_multi_future...` 失败：`tests` 不是可导入 package；没有执行测试体。
2. 直接执行测试文件首次失败：未设 `PYTHONPATH`；没有执行测试体。
3. 设定 `PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin` 与 `PYTHONDONTWRITEBYTECODE=1` 后，1 test / 1 pass，elapsed 0.004 s。

这是 CPU/mock 回归，只证明 Run12 的明确 Python 变量作用域与 12+30 记账路径已走通；不代表 F4 physical root 通过。
