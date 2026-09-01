# Expired Unconsumed Consolidation Run2 Bundles V1

状态：`EXPIRED_UNCONSUMED_DO_NOT_RUN`

8 个 run2 jobs 在 GPU0–7 全部被外部任务占用期间到期。到期后逐项确认：8/8 未消费、Guard 不存在、output 不存在、job cache 不存在，GPU execution=0、trajectory=0。

Machine evidence：`EXPIRED_UNCONSUMED_CONSOLIDATION_RUN2_BUNDLES_V1.json`，payload `f1559b1764cba91cf4e6cd695e5dfbd8381f07c4032cfb0fd19a9e155ae9f04d`。

Run2 永久禁止执行；任何新运行必须使用新的 authorization identity，并重新执行完整 fresh GPU scan 与 Guard recheck。
