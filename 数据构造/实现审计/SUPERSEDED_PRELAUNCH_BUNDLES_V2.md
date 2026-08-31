# Superseded prelaunch bundles V2

V1.1 source下的F1/F3/F4 run2 bundles均已生成但从未消费，现统一标记：

`UNCONSUMED_SUPERSEDED_DO_NOT_RUN`

F2在写任何run1 artifact前发现absolute output与basename namespace的validator冲突并fail closed。三个旧bundle无Guard、ledger、cache、output或GPU进程，保持不可变且禁止执行。V1.2修复后F1/F3/F4使用run3，F2继续使用未写入的run1。
