# Stage 0 readiness — smoke v1.1

## STAGE0_TERMINAL_BLOCKED_BEFORE_STAGE1

F4 frozen-neutral provenance已在CPU层修复：canonical target spec使用immutable artifact实现exact identity，realized prefix replay继续使用独立physical tolerance；旧11.75cm drift可复现且新路径会消除，缺失binding时fail closed。

每条真正生成的Stage 0 trajectory必须同时生成独立MP4；无trajectory失败明确记录不适用。MP4 writer、hash、receipt、family/finalizer强制合同已通过5项CPU测试。

Active/snapshot各`512/512` tests通过，180个source与92个test Python文件compile通过，byte-equal=true。Source=`41a6ede4e2b4dea01e7587ead948358023aeae2972006c31fce076bb96b31063`。

Single-use F4 v13 Gate已通过：22个真实candidate corridor queries、全部binding/spec/physical/receipt/cleanup Gates通过。四条corridor均planner失败，这是合法pilot evidence；F4 root以shared blocker进入Stage 0。

Canonical manifest=`b0e1db84ed883687d4de1caf3426bbef87b297bad3013f31d8ee9f8511eaf69c`的12个attempts均已终止：F1 3/3 pass；F2 3项infrastructure failure；F3 3项physical execution failure；F4 3项planner failure。共生成3条raw和3个MP4。

Canonical finalizer为authoritative但`stage0_completed=false`，因为F2 outer/pipeline未通过。因此当前停止并等待审阅；Stage 1、360 formal、training、H-reveal、compression和π0.5仍未授权。
