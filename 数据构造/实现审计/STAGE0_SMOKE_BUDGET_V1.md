# Stage 0 smoke finite budget v1

| Scope | Planner limit | Execution limit | Timeout |
| --- | ---: | ---: | ---: |
| F4 candidate-hash infrastructure | 48 | 0 | 7200 s |
| Stage0 F1 root A | 64 | 3 | 7200 s |
| Stage0 F2 root A | 64 | 3 | 7200 s |
| Stage0 F3 root A | 96 | 3 | 10800 s |
| Stage0 F4 root A | 96 | 3 | 20400 s |

每个scope最多启动1次，automatic retry=false，recovery=0。Stage 0的12个planned attempts均必须有终止回执，但不要求12条成功trajectory。Family-level jobs可在GPU0–7中不同的fresh-idle卡上并行，一卡一job、一family root不拆分。
