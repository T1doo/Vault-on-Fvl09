# CPU验证范围

- tools/plan.py真实生成并检查40主root+16reserve，3×3矩阵、split×difficulty、参数签名唯一、观测hash必须pending；不验证IK/实际current。
- tools/test_cpu.py：6/6通过；调用真实plan.validate、portable.verify/safe；坏矩阵/重复参数/伪造hash/路径逃逸/损坏与缺失文件均拒绝。
- tools/check_sample.py：独立package reader读回，审计hook禁止访问原datasets、active项目、Vault；结果MIGRATION_SAMPLE_RESULT.json，pass=true。
- tools/inventory.py：F1跨目录七项身份检查通过，统计48个引用的实际文件；只解析已存在最终回执，截断provisional不升级为有效JSON。
- 未运行SAPIEN/planner、GPU、模型或全量复制；未执行旧display计划。
