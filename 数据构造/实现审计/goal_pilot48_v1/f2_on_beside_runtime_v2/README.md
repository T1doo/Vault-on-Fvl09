# JSON同值序列化修复

原final语句返回的三个np.bool_字段在新模型save→digest边界导致TypeError。`runtime.LiveBackend.final_gate`只将NumPy scalar变成同值Python scalar，不改判断、窗口、动作或参数；NaN仍由原allow_nan=False拒绝。
消费前提/模型/Goal计数/清理继续复用原单关系资格。`qualification.py`、`runner_bridge.py`私有globals把新LiveBackend注入，原执行source保持原字节。
未来beside纯入口：`runtime.issue_f2_beside_serialization.build_manifest(job_id,reservation)`；只构造新beside job，不跑on、不写reserve，4/1/1/0、10高层checks、child1800/lease1980不变。
on当前成功动作可通过 `f2_on_final_serialization_review_v1/recover_v2.run()` 的追加式原谓词恢复独立审阅，原失败receipt不覆盖；恢复不是root/pilot登记。
RECOVERY_REVIEW002补完整Robot/Base_Task开爪语义源码及稳定serialization helper绑定；001作为原历史保留。
