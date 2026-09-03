# V2.3.1b Guard Prevalidation Repair Contract

Status: `CPU_SOURCE_REPAIR_VERIFIED`

This repair fixes only the Guard-receipt lifecycle conflict exposed by the sealed S1 failure. It preserves legacy V2.3.1a receipt compatibility, keeps output O_EXCL strict, and permits a preclaimed or active Guard receipt only through narrowly validated states and authorization bindings. It also adds a production API for terminalizing failures that occur before child launch.

Focused tests passed 4/4, including a real Guard-main subprocess stopped by a fake busy-GPU admission check. Active and review-snapshot full suites each passed 776/776 and are byte-identical.

Contract SHA-256: `708b0f13eb7a659222930a9f3c3936da2afd4d69bc64f22d0d93bb9aaef3b305`

