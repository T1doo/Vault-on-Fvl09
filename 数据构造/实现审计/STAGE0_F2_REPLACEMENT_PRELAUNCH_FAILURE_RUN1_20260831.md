# F2 replacement v1.2 run1 prelaunch failure

Run1没有启动child、SAPIEN或F2 attempt。GPU4两次fresh-idle检查均通过，per-GPU lease正常获取并释放，job cache完整清理；Guard在one-shot authorization消费前因validator接口缺少`expected_seed`参数而fail closed。

```yaml
status: failed_guard_internal_prelaunch
physical_gpu_index: 4
authorization_consumed: false
child_started: false
scene_created: false
f2_attempts_consumed: 0
gpu_lease_released: true
job_cache_cleanup_succeeded: true
gpu4_post_state: 12MiB / 0% / P8
```

这是纯Guard/authorization adapter兼容错误，不是F2 infrastructure slot、planner、physics或verifier结果。Run1 Guard receipt保留不可变。修复只增加Guard既有调用参数`expected_seed`与`expected_reviewed_content_commit`的显式validator支持；未修改layout/spec/program/object/arm/verifier/budget。

修复使用新source hash、新authorization ID、新Guard/output namespace；旧authorization不覆盖、不消费。Focused/active/snapshot tests重新通过后才签发run2。
