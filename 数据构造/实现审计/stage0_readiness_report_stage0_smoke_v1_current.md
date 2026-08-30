# Stage 0 readiness — smoke v1

## BLOCKED_WITH_REASONS

CPU实现与active/snapshot `481/481` tests仍成立，但唯一F4 infrastructure run没有通过Stage 0前Gate。Pristine与canonical prefix完成；第一个fresh candidate的前七个segment完全一致，只有`A_neutral`相对冻结contract产生`0.1174670097 m / 0.0079977769 rad`偏差，因此在任何corridor planner query前fail closed。

本次实际计数=`10 planner/0 execution/0 recovery`；10次planner query全部属于canonical prefix，corridor query=`0`。三场scene cleanup、activity-monitor恢复、source lock、GPU0释放和orphan=0全部通过。Single-use授权已消费且禁止retry，所以未生成canonical 12-attempt manifest，Stage 0=`0/12`。

当前最小代码根因边界是：suffix contract的branch-neutral由canonical prefix的`common_center_high`定义，但fresh scene在prefix replay后又从已经移动到tray的`common_x`重算该target。下一安全动作是先审阅并版本化“复用冻结canonical neutral，而不是从post-prefix actor重算”的collector修复；新GPU运行需新授权。

Stage 1、360 formal trajectories、training、H-reveal、compression和π0.5仍未授权。
