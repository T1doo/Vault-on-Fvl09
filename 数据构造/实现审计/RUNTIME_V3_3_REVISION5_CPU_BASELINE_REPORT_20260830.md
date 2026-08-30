# runtime-v3_3 revision-5 CPU baseline

## 结论

revision-5 active source 与 Vault 审阅快照均通过 `339/339`，source/tests byte-equal，三组独立 P0 审计未发现剩余确定性 GPU 前 blocker。

## 三项修复

- F2：只把经过 live topology 验证的 `fl_link6` palm 加入合法 body-pair assembly；raw selected-contact 与连续抓持仍必须由 finger-only `fl_link7/8` 证明。路线、target、support boundary、predicate 和阈值均不变。
- F3：V/H、幅度、顺序与 shared prefix 完全不变；仅对 return preplace/release controls 做统一 2× time dilation，在 original pad target 上方 1 cm contact-free release。pre-open 和 physical release 均检查完整 gripper assembly、实际双指开度、无重接触至 +250 帧；classifier sample tuple保持原 preregistration。
- F4：common-X release 后新增 vertical withdraw，并以既有 `common_center_high` 作为高位 neutral。revision-5 只执行 A top-down grasp + 20 mm micro-lift；pregrasp/grasp 必须实际到位且全窗口无碰撞，微抬全帧检查双指接触、A 离桌、common-X/B/C noninterference、tray predicate 和 support/stability。

## 授权边界

机器 scope map 仅允许 F2-r5 full root、F3-r5 full root、F4-r5 micro。F1、F4 full、IK、prefix smoke 和其他 revision 均被拒绝。每项 single-use、finite timeout、no automatic retry、recovery=0。

```text
implementation_source_sha256 = 0d19e5d0ace6f3115c686a77485f72b12858023e18dd0cab3fc49f610aa0b33b
budget_receipt_sha256 = ec79e21abc2a2e4c71f47a49df59f6c37c6a8db2bbaf752ac3b28c6af482b535
active tests = 339/339
snapshot tests = 339/339
diff = zero
```

本报告不授权 Stage 0，也不是 GPU 成功证据。
