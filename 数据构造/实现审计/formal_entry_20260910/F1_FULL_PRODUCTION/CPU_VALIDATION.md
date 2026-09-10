# CPU验证记录

所有记录均是CPU检查或明确synthetic后端的接口测试；GPU初始化、真实规划/采集、训练和HD新增均为0。fixture只替换模拟器与GPU宿主机制，计划、状态机、原始文件保存、独立cell/root门、模型出口、账本和副本使用实际实现。

| 记录 | 已完成结果 | 范围 |
|---|---|---|
| CPU_FULL_FAMILY_TEST_round1.log | 8/8，356.028秒 | 十root/90格、18→90自动继续、拒绝错误主槽映射、reserve/重启、false授权 |
| CPU_FINAL_TEST.log | 81/81，609.759秒 | 全族、物理负例、逐cell门、launcher异常/恢复/源码兼容、anchor/copy、场景计划 |
| INDEPENDENT_VERIFIER_CHECK.log | 4/4 | 独立构造的移动pose+零速度、右臂控制、实际开爪反例 |
| LAUNCHER_CHECKS.json | 25单元+3真实接口链 | 异常lease证据、已成功raw保护、缺失格resume、copy-only、source-only兼容 |
| COPY_ANCHOR_REPORT.md | 原定向7项及旧回归11项 | 文件完整性与anchor/数组物理等价、禁原路径、copy故障恢复 |
| INDEPENDENT_ANCHOR_REVIEW.md | 原18项及新增根头反例复核通过 | 独立复核副本/anchor实现，发现并关闭根头与nested身份缺口 |

81项通过后，仅新增了副本根头与nested身份绑定检查，以及reserve spec对激活原件的直接hash/原主槽引用。最终受影响回归记录在`CPU_FINAL_AFFECTED_TEST.log`；全族结构化结果为`CPU_FULL_FAMILY_RESULT.json`，其中`synthetic=true`、`physical_collection_increment=0`。最终封存检查必须核对该结果的source bundle与`SOURCE_FREEZE.json`一致。

执行环境与方法见`CPU_ENVIRONMENT.json`；使用`/nfs_share/lijunhui/Robotwin2/env/bin/python`、`PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin`、`PYTHONDONTWRITEBYTECODE=1`。

```sh
python -m unittest test_f1_full_production test_f1_verifier_cell test_family_entry \
  test_first_wave_launcher test_launcher_recovery test_launcher_real_pipeline \
  test_anchor_copy_v1 test_portable_v2 test_formal_export test_scene_plan -v

python -m unittest test_f1_full_production test_anchor_copy_v1 \
  test_portable_v2 test_formal_export test_scene_plan -v
```

完整测试中两个GPU替身job可并行；测试账本的场景计数是模拟调用计数，绝不进入正式数据计数。fixture原件由各自TemporaryDirectory清理，不保留为真实数据；可按上述命令复现。第一次完整测试的ResourceWarning属于测试读取CSV后未显式关闭文件，已在最终测试中改为context manager，不涉及生产数据或GPU。

本轮没有证明新场景的原生可达、抓取、相机同步/渲染行为、实际RSS/耗时或统计泛化；这些保留为未来授权后首批和逐root的实测项目。

最终受影响回归完成：**35/35通过，444.967秒**。最终`CPU_FULL_FAMILY_RESULT.json`重新完成十root/90格，并与`SOURCE_FREEZE.json`的bundle `4cb9c19a04211edbea2fecbd7474ff6d0d913061ebe63c2af6f0a3092b22c81a`一致。最终源码上的源/配置/预算/授权封存检查64项通过；正式授权文件仍全false。

发布前格式检查记录：`git diff --check`指出`native_f1_orchestrator.py:778`的一处行尾空格；这是不影响Python语义的格式项。本次保留已经完整执行测试并封存的原字节，未将该格式检查报告为全通过。
