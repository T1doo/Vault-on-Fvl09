# runtime-v3_4_1 finite nonformal budget

本预算由用户对 one-shot work package 的批准约束，仅用于非正式 pre-Stage0 证据。GPU scope 只可在 physical GPU0 独立 fresh-idle 时串行启动，每 scope 最多消费一份authorization，recovery=0，无自动retry。

| Scope | Planner limit | Execution limit | Timeout |
| --- | ---: | ---: | ---: |
| F1 shared regression | 64 | 3 | 7200 s |
| F2 inside targeted v11 | 32 | 1 | 7200 s |
| F3 three-context targeted v11 | 48 | 3 | 10800 s |
| F4 exact corridor + A v11 | 64 | 1 | 14400 s |
| F2 conditional full root | 32 | 3 | 7200 s |
| F3 conditional full root | 96 | 3 | 10800 s |
| F4 conditional B/C preflight | 32 | 0 | 10800 s |
| F4 conditional full root | 96 | 3 | 20400 s |

Static exact/source envelopes分别为 F1 46/3、F2-targeted 22/1、F3-targeted 42/3、F4-corridor+A 58/1；条件 full scopes为 F2 32/3、F3 96/3、F4-B/C 26/0、F4-full 82/3。前置 Gate 失败时必须保留更小的实际计数并终止该family。

终端实际消耗：F1=`46/3/0`，F2=`22/1/0`，F3=`7/0/0`，F4=`10/0/0`，合计=`85 planner / 4 execution / 0 recovery`。F2/F3/F4 targeted均未通过，因此conditional scopes签发数=0。没有超预算、没有retry、没有recovery。
