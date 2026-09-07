# on修订1终结：不是已知物理失败，而是final回执序列化异常

`p48_f2_on_release_revision1_001`四个规划/执行、两次native筛查、原held transport、实际released fullworld均pass；suffix错误为 `TypeError: Object of type bool_ is not JSON serializable`。
原final文件不存在，不能据此前置成功直接说final通过。原suffix.pass=false、scientific_route_pass=false和所有原bytes保留。

独立CPU恢复读取已封存trace末50帧**原始完整contact_pairs**、角色姿态/线角速度、EEF、gripper命令，结合实际asset config/角色名称/scale及绑定cavity/footprint，执行原Actor.get_point API（CPU Pose）和原final AST语句，不创建Simulator Scene。
11个原checks全部true：目标on、排他、50帧稳定、连续支撑、开爪、rest位置/方向、EEF线/角静止、held、inside专属项不适用。没有改阈值/窗口/接触身份。
同一结果原样hash能精确复现bool_异常，只有三个字段是np.bool_：`checks.rest_position`、`checks.eef_linear_stationary`、`checks.eef_angular_stationary`。转换为同值Python bool后可正常保存，false仍false。

`RECOVERY_REVIEW_001.json` receipt `936f025a0a27f3d106619354248d1b6f6613bd553f0a2b4357da62d9e50ef076`是append-only派生final复核，不篡改旧终端，也不自行授予root/pilot接受。主线程可单独核对完整来源及资源链后显式采纳on资格；不建议重跑已成功动作。

唯一修复在新 `f2_on_beside_runtime_v2`：仅final receipt边界做严格同值numpy→Python转换，未改模型、目标、物理动作或verifier语句；不允许NaN，未提供任意对象字符串兜底。`runtime/issue_f2_beside_serialization.py`为未来未尝试beside接入新wrapper/bridge的纯builder，不重跑on、不写reservation。

inside当前独立final路径并非同一原AST结果直接hash：已对这三项显式bool转换，并经其physical_gate/geometry自身封存；只读检查未见这次同源问题，不能由此泛称inside所有未来路径已验证。
首次CPU恢复尝试导入完整envs包触发无关clutter相对路径FileNotFoundError，未输出恢复回执/未GPU；随后只提取原Actor API类，最终恢复正常。两次CPU运行不计作物理尝试。
