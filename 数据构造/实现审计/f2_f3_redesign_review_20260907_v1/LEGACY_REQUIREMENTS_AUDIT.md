# 旧要求排查与新任务边界

2026-09-07，V2。用户最新明确：“不要继承旧goal的要求了，我们是全新的”。本表替换尚未发布的V1继承方案。

2026-09-08补充：用户已采纳GPT七项修改，现行主计划/附录为V2.1，交接说明已就绪。下文V2“当前仅审查/待交接”是前次状态，不要求Luna重新外审。新清理口径分owned_cleanup_pass/device_idle_observed，外部后占卡且owned已清理不阻塞其他卡；后缀允许按冻结规则在线规划，qualification不等于collection，已知超额如实落账。旧“等他人卡回baseline”“后缀零solver”“stage间调配再审批”“趋势风险无限暂停”等约束不得带入新任务。具体按V2.1附录，不从旧Goal导入新预算/门限。

## 当前结论

本轮为独立F2/F3重设计任务。旧 `cmf_pilot48_20260907` 的GOAL、CONTRACT、STATE、预算账本和单次审批均只说明历史事实，不作为新任务上级合同。不继承旧余额/消耗/修订计数、串行限制、逐次审批链、暂停状态、跨两族连续6条或formal草案完成条件。

用户本轮有效要求：先写计划供GPT审查再交Luna；独立空闲GPU0–7可并行；新日志；精简AGENTS；每完成阶段自动commit/push私有Vault/main。保留已成功F1/F4数据及旧失败证据。研究语义、真实性和工作区/他人资源边界是独立规范，不因旧Goal退役而失效。

## 检查范围与发现

范围为工作区/同步Vault AGENTS、新计划/日志、其引用的历史GOAL/CONTRACT/STATE、runtime/runtime_v2/runtime_v3、激活脚本和操作手册。未声称全仓历史文字已被清除；原始记录必须保留。

| 位置 | 残留要求/问题 | 新任务处理 |
| --- | --- | --- |
| goal_pilot48_v1/GOAL.md:22、CONTRACT.json:15 | 同时1张卡 | 整份旧合同仅历史；新任务独立多卡合同 |
| 三版runtime/budget.py:44 | 第二reservation拒绝 | 不直接继承；新调度预算支持多job事务和总额校验 |
| 三版manifest_contract.py:18、runtime/issue*.py | 强制gpu_jobs_serial=true | 新issuer/validator/合同一致实现；不是只改flag绕过Guard |
| runtime/reconcile.py:23、reconcile_display.py:38、reconcile_root_resolution.py:71 | running单值置空 | 新任务逐job状态、幂等清理，不能覆盖其他在途job |
| 旧STATE、budget_ledger、failure_revisions | 旧余额及耗尽修订上限 | 只读历史，不恢复、不carry-forward；新预算和修订规则在V2计划独立提出并待审 |
| 旧Goal连续6条/formal草案 | 无关附加完成要求 | 已从本次完成条件删除 |
| 操作手册§6.2/§8.4 | 数字GPU1示例及collect_data.sh覆盖CUDA_VISIBLE_DEVICES | 通用旧例非新作业入口，新作业fresh Guard/UUID绑定 |
| config/activate_robotwin2.sh:16 | 旧枚举验证注释 | 实际不硬编码卡、不恢复fvl09白名单，且unset LD_LIBRARY_PATH；无需改其设备策略 |
| 旧日志、分享原文、旧AGENTS备份 | GPU串行、继承旧Goal、旧固定资产/姿态/物性要求 | 原文留作历史，已被本次最新指令覆盖，不自动导入新任务 |
| 旧F3 STATE/总handoff | 摘要停在更早的CPU或lift-model阶段 | postlift报告证明最后横放已离台但失稳；只修解释，不倒写旧记录 |
| create_actor/Actor、旧设计字段 | mass-only覆盖、metadata覆盖scale、scene material冒充shape材料 | 作为根因线索审查，不能保护为新任务不可变规则；新factory实测并独立设计 |

## 实施前必须分清

新运行层尚未实现，当前仅审查和文档发布。Luna按V2计划建立独立namespace/合同/STATE/ledger；可按hash和具体职责复用稳定技术组件，但不得导入旧Goal授权/状态副作用。预算按新任务共同总额管理，不给每卡复制一份，不无限重试。

历史审批无需逐条“撤销”，也不需要为了摆脱旧串行限制再问用户；它们不控制本轮。新方案实施仍等待本轮计划审查和明确交接，不是受旧暂停束缚。GPU前后检查、owned cleanup、数据真实性和科学Gate保留。
