# Superseded prelaunch bundles V1

F1、F3、F4的旧source=`9a0b7a9e…0c65` run1 bundles已生成但从未消费，现统一标记为：

`UNCONSUMED_SUPERSEDED_DO_NOT_RUN`

F2在写任何bundle文件之前发现canonical `receipt_sha256`与execution-layer `authorization_sha256`互相包含的不可满足hash循环，因此F2没有生成REQUEST/SOURCE/AUTH。

三个旧bundle均没有Guard、consumption ledger、job cache、output或GPU进程。旧artifact保留且禁止执行。修复后F1/F3/F4必须使用新run2 namespace；F2可继续使用尚未写入的run1 identity。Stage 0、Stage 1与formal边界均不受影响。
