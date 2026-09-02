# Post-Stage-0 Generation Repair V2.2 impact report

Generation Repair V2.2 已在 CPU/source 层实现并验证；它没有执行 planner、GPU 或物理动作，也没有生成 trajectory。

## 实现结果

- F2：把错误的“抬升前必须离桌”拆成 pre-lift 与 post-lift 两个 Gate；25 mm qualification micro-lift 后保持 50 frames，才检查 off-table、contact/identity continuity 与 5 mm/50 mrad transform drift。目标 actor pose、opening normal 与 horizontal margin 由 scene/binding/certificate 内部派生；执行器不再接受四个外部几何参数。
- F3：新增官方 raw-pose generation receipt，绑定 asset/arm/contact/rotation/pregrasp/actor pose/generator/raw hashes；新增独立 Stage-A 与 Stage-B purpose/spec/runner。Stage A 单独永不 candidate-ready。
- F4：spec 强制绑定 `F4-ABC/F4-ACB/F4-BAC` 与对应 order；每个 hv2 candidate 必须在三个独立 fresh/reconstructed scenes 完成三程序资格检查。scene 建立后先核对 actual source layout，再以实际 source pose 重跑 geometry V2。

## 验证

- Active/snapshot source：276 Python files，tree `a23b3c717428ed6ea45d9fb2cebf1940258a66630a021e79498231a6fb200a26`，byte-equal。
- Active/snapshot tests：140 Python files，tree `557325c1333ea825bbc673fb433ad9b87bc76ea4f7cdef5a3a9e533fb62838a4`，byte-equal。
- Final full suites：active `741/741`（394.691 s）；snapshot `741/741`（394.057 s）。
- 首次 snapshot full 为 `740/741`：新增 test fixture 误用历史 module-relative asset helper；已改为 certificate-bound canonical asset hash 并双侧全量复验。另保留一次旧 nominal receipt order 兼容性回归和一次错误 unittest 入口失败。

Report payload SHA-256：`9b5c915312afb514d609d41a899fcdcfce8d9a88e6ec3a699e8ff3654698b80d`。

## 结论边界

F2/F3/F4 均为 `implemented_and_cpu_verified`，不是 planner-qualified、runtime-qualified 或 scientifically supported。F1 保持历史 candidate-ready；统一 Stage 1 仍为 `NOT_READY_NOT_AUTHORIZED`。Stage 0 保持 `STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE`，formal root/trajectory increment 均为 0。
