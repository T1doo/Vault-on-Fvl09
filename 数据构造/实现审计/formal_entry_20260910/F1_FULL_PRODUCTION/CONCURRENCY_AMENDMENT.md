# F1 并发配置修订

用户在执行前明确要求允许超过两张卡并发。本次只扩大调度并发上限，不扩大总预算、不改变每 root 的 attempt/cap、验收、reserve 或科学合同。

- `max_concurrent_gpu_jobs = 8`
- `max_gpu_jobs = 8`
- `max_cpu_finalizers = 2`
- `max_copy_workers = 1`
- 可用物理卡仍固定为 GPU0–7

每个 wave 重新获取完整 GPU 快照，只有同时满足 Guard、UUID 锁、近基线 memory/utilization/P-state 和无其他 compute process 的卡才会派发。空闲卡少于8张时按实际空闲数运行；不共享忙卡，不因并发配置等待或占用不合格设备。每个 root 仍固定一张卡，恢复不会改绑到另一张卡。

201600秒仍是全族共享的保守 lease 上限；并发只缩短墙钟时间的可能性，不改变累计 GPU 秒预算。CPU 收尾和复制上限保持不变。CPU fixture 与 preflight 已按新配置重新验证，fixture结果不计入正式数据。
