# Stage 0 readiness — smoke v1.1

## READY_TO_RUN_SINGLE_F4_V13_INFRASTRUCTURE_GATE

F4 frozen-neutral provenance已在CPU层修复：canonical target spec使用immutable artifact实现exact identity，realized prefix replay继续使用独立physical tolerance；旧11.75cm drift可复现且新路径会消除，缺失binding时fail closed。

每条真正生成的Stage 0 trajectory必须同时生成独立MP4；无trajectory失败明确记录不适用。MP4 writer、hash、receipt、family/finalizer强制合同已通过5项CPU测试。

Active/snapshot各`512/512` tests通过，180个source与92个test Python文件compile通过，byte-equal=true。Source=`41a6ede4e2b4dea01e7587ead948358023aeae2972006c31fce076bb96b31063`。

当前只允许运行一个single-use、planner-only F4 v13 Gate。Gate必须达到至少一个真实candidate corridor planner query；corridor物理成功不是前置。若Gate通过，直接生成12-attempt manifest并运行4×3 `r_pc` Stage 0；F2/F3无需预先修成功。

当前Stage 0=`0/12`。Stage 1、360 formal、training、H-reveal、compression和π0.5仍未授权。
