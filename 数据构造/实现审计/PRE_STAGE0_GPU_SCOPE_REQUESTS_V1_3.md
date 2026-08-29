# Pre-Stage-0 GPU Scope Requests V1.3

```yaml
status: terminal_family_scopes_blocked
a0: passed_nonformal_A0
accepted_real_roots: 0
new_gpu_launch_authorized: false
stage0_authorized: false
```

V1.3 supersede V1.2作为current GPU scope入口。所有本轮authorization均已消费，不可重放。F1/F3达到repair停止线；F2/F4有hard blocker。F4末次postcheck发现外部GPU进程，当前卡后续运行停止。

任何新GPU工作必须先有新的impact-reviewed implementation/design version、预算、request/source-lock/authorization namespace和fresh-idle guard；不能延长或恢复本轮次数。
