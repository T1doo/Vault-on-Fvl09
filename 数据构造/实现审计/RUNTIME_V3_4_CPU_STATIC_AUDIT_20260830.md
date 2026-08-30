# runtime-v3_4 CPU/static 审计

## 结论

`PASS_PHASE0_CPU_SOURCE_FROZEN / BLOCKED_BEFORE_TARGETED_GPU_RESULTS`

Active additive source与Vault review snapshot byte-equal，source SHA均为`1cadd3e28af56f56c32e8fe363fbeb3c2f3397ff196a63c6bd115285aa85b316`；两侧各`449/449` tests passed，218个Python文件compile检查通过。官方tracked baseline仍为`c3ddfa8b97d5519efa828b075999bd0006778e5e`且tracked-clean。

三份旧证据法证artifact已经不可变写入并校验：F2=`2919e984…6dab3`、F3=`23024fd4…fee4f`、F4=`48b1ec4c…5dd4c`。

## 冻结实现

- F2：`F2ReleaseSafetyGateV10 → full-open → exactly 250 settle frames → F2FinalInsideSuccessGateV10`；安全Gate不再要求最终full-OBB/0.05 rad/s，最终verifier阈值完全不放宽。
- F3：三个program统一使用官方contact-point 0/candidate 0中段侧抓、close target 0.0与250帧post-close settle；targeted Gate只执行shared V后一个suffix event并在release前停止。
- F4：固定四个planner-only corridor，按顺序选择首个完整chained endpoint/IK/collision/joint-margin pass；然后A-only→B/C/AB→完整root，任何上游Gate失败都停止。
- GPU：runtime live discover physical GPU0–7；独立fresh-idle、一卡一job、family-level parallel、root不shard；每job独立authorization/consumption/Guard/UUID/PGID/namespace/timeout/post-release。

由于共享root-orchestrator、planner-audit helper和Guard dispatch发生了兼容性修改，Phase 1必须同时运行一次`F1_shared_regression_v3_4`。它只是回归，不覆盖或重新定义历史accepted F1 root。

本阶段没有运行GPU/SAPIEN；Stage0/1/formal/training/H-reveal/compression/π0.5仍为0/未授权。
