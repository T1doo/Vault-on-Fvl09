# runtime-v3_3 canonical-prefix real smoke

状态：`PASSED_NONFORMAL_CANONICAL_PREFIX_REAL_SMOKE`。

在physical GPU0上生成一次F1 canonical prefix，并在三个独立fresh scene逐step replay同一artifact：

```text
semantic prefix steps: 793
prefix action SHA-256: 22f8c7c2f1066672c715df94abc79636915b6406dd6046e6fbb6a8d132395069
artifact SHA-256: 65937f11aefe64bb966983b88d33d1beaa0c40bb8b0b4ced545772e1d716cf4f
settling: 50 steps，明确排除semantic P
```

三条replay均满足：action/requested/mask和底层gripper drive arrays哈希一致；planner delta=0；prefix-end anchor等价；physical acceptance通过。五个scene cleanup全部安全、orphan=0。Guard无timeout、child exit=0，post-release verified；独立postcheck为GPU0=P8/14 MiB/0%/无compute process。

本scope是nonformal架构验证，不是Stage 0轨迹，不计入12/48/360分母。它证明strict-prefix artifact/replay机制在真实SAPIEN中可工作，不证明F1–F4完整root已通过。
