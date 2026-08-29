# F1 strict-prefix root revision-2 accepted report

## 裁决

F1已形成第一个完整`accepted nonformal pre-Stage-0 root`。它不是Stage 0轨迹，也不进入正式360条分母。

固定同一slot/seed/layout/left arm/RGB roles/plasticbox/base3/candidate universe；三色统一使用planner-assisted grasp、4 cm+4 cm lift和cluster-center carry hub。结果：

| Branch | Planner API calls | Real execution | Semantic verifier | Raw actions/states |
|---|---:|---:|---|---:|
| red | 15/15 | 1 | pass | 4163/4164 |
| green | 15/15 | 1 | pass | 4048/4049 |
| blue | 15/15 | 1 | pass | 4210/4211 |

每个branch均通过：true cavity OBB、非目标位移、连续box contact、pose稳定、夹爪打开、rest pose/速度。Posthoc从immutable trace补查的最后50帧目标方块angular speed三色均为0，也通过当前更严格angular stable Gate。

## Strict-prefix与root原子性

- canonical prefix 793 steps，action SHA=`22f8c7c2…95069`；
- 3个suffix preflight与3个branch均fresh scene；
- 三分支current/anchor、prefix bytes/steps/start/end与gripper drive hashes一致；
- target role在prefix不可见；execution planner delta均为0；
- root finalizer的3/3 branches、candidate-prefix link、final-state equivalence、root cleanup全部pass。

总预算：planner=46、execution=3、recovery=0。11/11 scene cleanup安全、orphan=0。Guard GPU3 child exit=0、无timeout、job cache清理、GPU lease释放、post-source-lock与post-GPU release全部pass；独立postcheck=P8/15 MiB/0%、无compute。

Evidence namespace有42个文件，tree SHA=`47114cbc9bd940311a3f658e2155ce6a8332635f6a92ef8837bd7de7166444a0`。

## Claim boundary

当前可以说F1一个非正式root的三候选strict-prefix全管线可行。不能说Stage 0 ready、F2–F4可行、已有formal data、H-reveal/temporal identifiability/compression/policy transfer成立。
