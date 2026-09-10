# F1全族生产准备交付

唯一交接入口：[LUNA_F1_FULL_PRODUCTION_HANDOFF.md](LUNA_F1_FULL_PRODUCTION_HANDOFF.md)。

状态：CPU_READY_AWAITING_ONE_FULL_F1_EXECUTION_APPROVAL。10主root/90格及4有序reserve已准备；真实GPU/采集增量为0，执行授权全false。未来获批后最多并发8个独立空闲GPU作业，首18条是自动检查点，不再另请余下72条批准。

- [五项修复](FIX_CLOSURE.md)
- [完整计划](PRODUCTION_PLAN.md)
- [统一预算](F1_BUDGET_REQUEST.json)
- [CPU验证](CPU_VALIDATION.md)
- [独立检查](INDEPENDENT_REVIEW.md)
- [封存核对](PACKAGE_FREEZE_REVIEW.json)
- [源与配置锁](SOURCE_FREEZE.json)
- [存储事实与限制](STORAGE_PLAN.json)

源码归档包含项目Python、实际配置和URDF/SRDF；30个机器人mesh文件只冻结hash，不把约380MB资产重复提交Git。模型数据副本的standalone读取不依赖这些仿真资产，但不能把数据副本称为完整模拟器安装或异地备份。
