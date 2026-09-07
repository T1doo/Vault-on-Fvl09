# on → beside 两个 fresh scene 资格检查

固定先on后beside；任一current、anchor、prefix、模型、规划、native、执行、物理门、保存或cleanup必需项失败，保留该分支证据并停止，后一分支不尝试。
共享清单仅控制两个串行scene，不分卡、不shard；每scene真实重放clearance001 canonical prefix，0新增prefix solver，不重新运行其资格或恢复旧held态。
原current严格一致；actual initial anchor经原compare_anchors等价并明确reference/actual绑定；原prefix physical Gate必须重新通过。

上限8实际MotionGen问题、2 fresh、2 action、0 collection；on6/beside10独立高层start检查另计，不混进solver问题。
每个suffix只有4个新规划机会，无失败重试；第一分支失败可只消费前半预算，实际local counters与V3 CHARGE逐项对账。
child timeout=3600秒（2×1800工程上限），lease=3780秒（child+180秒Guard窗口）。实际prefix001整job135.51秒仅是历史时间参考；包含两次fresh/render/model/native检查/物理suffix，1800每分支是有限保守分配，不宣称性能已验证。
当前实现使用共享3600秒总deadline；没有隐含每分支重试或额外lease。后续精确Guard仍须fresh GPU0–7/UUID/pre-post/owned cleanup。

`runtime/issue_f2_on_beside.py` 仅消费主线程已有reservation纯构造manifest；不reserve、不写jobs、不启动GPU。
迁移runtime_v3 Guard/runner/meter；须锁继承parent所有源/输入及新suffix/qualification/live_models源。
仅两分支资格，不证明inside、不依赖inside未决接触许可、不冻结三候选宇宙、不接受F2 root或pilot raw。
fixture tests只CPU；所有正常和异常trace/终端UTF8 exclusive保存，原成功prefix/F1/F4均不重采。
