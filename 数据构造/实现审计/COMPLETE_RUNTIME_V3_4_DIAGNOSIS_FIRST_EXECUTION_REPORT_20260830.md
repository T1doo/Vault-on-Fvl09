# runtime-v3_4 diagnosis-first 完整执行报告

## 裁决：BLOCKED_WITH_REASONS

通俗地说，这轮把“为什么失败”看清了很多，但没有把F2/F3/F4完整跑通，所以不能进入Stage 0。

| Family | 真实结果 | 是否开放full root |
|---|---|---:|
| F1 | shared regression在三分支suffix planner计数一致性处失败；46 planner / 0 execution | 否；历史accepted F1保留，但v3_4 regression未通过 |
| F2 | inside真实执行在balanced release之前的旧angular-stability Gate失败；0.0793 > 0.05 rad/s | 否；新safety/final Gate未真正测试 |
| F3 | `D3-*`诊断别名被旧task-feasibility ID校验挡住；0 planner / 0 diagnostic execution | 否；不能称抓取假设失败 |
| F4 | 四个carry-mid全部真实planner成功，但全部在下一A_preplace失败；30 planner / 0 execution | 否；进入layout impact review |

### F2特别说明

不可变top receipt把本次写成0 planner/0 execution和cleanup uncertain，但更强证据表明：prefix有19个planner receipts、suffix preflight有3个，controller execution callback已进入并保存1969-row partial trace，因此审计计数应为22/1/0。四个scene cleanup records、Guard post-source-lock、orphan=0和GPU2 release全部通过。旧receipt不覆盖，另建reconciliation artifact。

### F4特别说明

Revision-9的carry-mid blocker已被实质推进：四个新carry-mid都可达。新的真正终点是A_preplace。由于candidate3/4 runtime只替换了carry-mid、没有落实contract中lower-preplace，当前证据不足以声称“完整四种预注册corridor都严格实现后仍失败”；但已足以拒绝A execution并停止扩大。

### GPU与安全

F1/F2/F3/F4分别使用physical GPU0/2/3/4并行。GPU1为外部忙卡且未使用；所有job admission/launch fresh-idle、无timeout、post-source-lock通过、task-owned orphan=0、Guard post-release verified。最终GPU0/2/3/4均回到基线，未干预GPU1外部任务。

没有Stage0、Stage1、360条formal数据、模型训练、H-reveal、compression或π0.5。
