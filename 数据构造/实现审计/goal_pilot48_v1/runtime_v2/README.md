# Goal runtime V2 live collection meter

旧runtime全部不改。budget.py逐字复制，ROOT仍goal_pilot48_v1；同CONTRACT/STATE/budget_ledger.jsonl/budget.lock，没有新账本。没有在本实现/测试调用reserve/reconcile/transact。

新manifest guard/runner路径必须指runtime_v2，source_files加入本目录及collection_meter_review_v1全部.py。migration.bindings(parent_manifest)只读核验并返回迁移source/input/entry映射，不签发、不改旧manifest。Guard全部GPU实时snapshot/UUID/lease/owned cleanup/cache/POST_CHILD逻辑保留，仅导入和RUNTIME路径转新目录。manifest与Guard内部导入都命名空间隔离，避免CPU加载旧runtime时串模块。

新Guard的_write_new定向接realization_utf8_io_v1.write_new，使收据也是UTF8 exclusive atomic；其余safety函数AST逐个与冻结Guard相等，main仅namespace imports变化。该writer不修改旧已保存Guard receipt。新manifest/input必须绑定UTF8 helper（旧parent已绑定时保留其hash）。

job设置requires_live_meter=true，dispatcher调用run(manifest,meter=meter)。root runtime必须在任何orchestrator调用前：

```python
with meter.instrument_adapter(adapter, source_profile_sha256=manifest['implementation_source_sha256']):
    result = orchestrator.run_nonformal_root(...)
```

realization runtime可用meter.instrument_collector_factory(pipeline,profile_for_cell=...)；作用于pipeline真正导入的make_adapter绑定，全部退出后恢复。source profile必须等于manifest活跃source。CollectionHook在strict_prefix_branch factory之前charge，factory/setup/后续任何失败均不退款；3个branch请求计3，不按生成raw数量计。runtime返回collection_attempts与scene_attempts和accounting_complete，dispatcher逐项对账；有collection cap却未装hook不得完成。老F3 run(manifest)仍兼容（requires_live_meter缺失/false且collection cap0）。

close回收所有hook和原meter类patch，active context未退出属于错误；关闭后不能再charge/event或装hook。重复close幂等。F1新增job在manifest和runner明确拒绝：旧F1 namespace DenseTraceMixin的action覆盖尚未审计，不能仅collection hook有效就把action漏成0。F2/F3/F4活跃source保持原Base_Task/DenseTraceMixin计量。

CPU dispatcher端到端fixtures覆盖3branch=3、factory失败=1、两family factory/hook恢复、closedmeter拒绝、旧F3不接meter、无hook拒绝、F1拒绝与预算ROOT/byte-identical budget验证。测试只mock Meter.install以避免导入CUDA/SAPIEN runtime，不创建GPU场景或真job/reservation。真实GPU验收仍待新授权job。
