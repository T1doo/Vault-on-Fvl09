# 下一执行窗口交接

当前Goal是生产准备与副本规划，非正式采集授权。P4两族24条保持完成；HD搁置。先读AGENTS、当前日志末尾、本文件、BATCH_READINESS_REVIEW、F1_F4_BATCH_PRODUCTION_PLAN、DATA_COPY_AND_MIGRATION_PLAN和PRODUCTION_BUDGET_PROPOSAL。源码基线31a0287；所有新文件在本目录，数据小样不入Git。

## 当前已完成/尚未完成

完成：四族真实入口审查；F1-red跨目录验收身份核对；56个planned slot草案/360目标矩阵与CPU验证；真实129MB单cell独立副本、禁止原路径回退读回；存储统计与一次性资源提案。

尚未完成：通用root ID/scene_spec全链路、正式九条执行/验收wrapper、四族统一portable root exporter、真实新场景qualification、split近重复与投影难度实测。没有把这几项标CPU_BATCH_ENTRY_READY，也没有启动GPU。工具只验证计划结构和单cell迁移，不给现有pilot套循环。

## 首族首批与实现顺序

1. 为F1扩展显式formal scene spec，保留成功F1BatchPilot adapter/primitive、raw writer和Guard；9条矩阵以new formal contract提供，不修改历史开发验收文件。
2. 正式wrapper实现冻结slot→三程序资格→candidate/task tree freeze→首cell产生本root prefix→9条新fresh scene→独立root验收→copy。collector、finalizer、source profile、variant要求都消费同一个spec。
3. 在CPU用真实CLI参数解析/dispatch seam验证通用ID、九格、scene参数进入factory、失败checkpoint及resume；不可用mock固定pass替代真实调用链。
4. 首波F1_000001(train clear)、F1_000002(train medium)，scene proposals见PLANNED_SLOTS。两root物理尚未验证；每root三单独资格scene+9采集scene，canonical prefix生成算在第一条采集，不另加一条。资格setup若动作同样计action，失败query照计。
5. 完成实现source freeze和用户一次预算/顺序解释批准后，才可绑定UUID运行。先2root完整18条，通过计划中的放量门再完成余8root；reserve严格rank替代，剩余family物理不并行。

现有真实CPU命令（在本目录）：

```
/nfs_share/lijunhui/Robotwin2/env/bin/python tools/plan.py --check PLANNED_SLOTS.json
/nfs_share/lijunhui/Robotwin2/env/bin/python tools/test_cpu.py
/nfs_share/lijunhui/Robotwin2/env/bin/python tools/check_sample.py /nfs_share/lijunhui/CVPR_FutureIntent_Data/reference/p4_v1/F2/F2-A-v2/beside/r_pc
```

拟新增物理入口接口（当前未实现，禁止直接执行）：
`formal_batch_driver --plan PLANNED_SLOTS.json --family F1 --roots F1_000001,F1_000002 --contract <approved_contract> --output <new_namespace>`。
后续执行者须先实现上述最小wrapper并跑真实CLI CPU seam，再把此模板绑定实际脚本/hash/输出。不能将本模板解释为现有可运行formal入口。

## 一次性预算提案

精确机读表见PRODUCTION_BUDGET_PROPOSAL.json；均未授权、未消耗，不继承P4余额。首波包含在90条中。每族按首波2root、余8root、4reserve和最多9cell恢复分列。成功样本基数360，最坏collect尝试540；资格可能有动作，按实际调用保守预留，不冒充成功采集。

| 族 | fresh/action上限 | collection尝试 | solver上限 | GPU lease上限秒 |
|---|---:|---:|---:|---:|
| F1 | 177/177 | 135 | 5100 | 73800 |
| F2 | 177/177 | 135 | 7200 | 73800 |
| F3 | 177/177 | 135 | 9300 | 86400 |
| F4 | 177/177 | 135 | 16020 | 149400 |
| 总计 | 708/708 | 540 | 37620 | 383400 |

F1首波（不含reserve/恢复）：fresh24/action24/collection18/solver600/GPU9000s。含整族reserve和恢复的总上限如上，不能每卡复制。每root资格预留900s，采集按F1/F2 3600s、F3 4500s、F4 9000s；不是耗时预测。实际运行前计量seam发现调用超出此分配则修改提案一次提交，不静默超额。

已保存cell elapsed区间：F1 205.7–235.1s(5条可解析)、F2 129.6–159.7s(12)、F3 133.7–165.4s(12)、F4 559.0–601.2s(6)。这些是cell局部计时，不含完整outer资源占用。90条×区间粗算每族单卡约5.1–5.9h、3.2–4.0h、3.3–4.1h、14.0–15.0h，合计25.7–29.0卡小时基数；scene变化、资格、失败、I/O和首波双卡调度另加，不能承诺一晚。正式通过率、cold-start、写盘/CPU验收/复制吞吐首波单独计时。P4的9600s是预算扣额，其中5000s保守核销，不用来算速度。

## 集中待用户决定

只需批准一个完整范围：最小入口扩展后，按40/360、56槽草案、预算表和逐族stage2→stage3方式启动；其中canonical原“先全40root freeze”与逐族采集的顺序解释需要确认。350GiB存储为提案，个人配额未确认。当前无GPU授权，首波物理条件pending，所有phase3真值hash必须实际生成。

共享代码错误停受影响批次；普通不可行保留失败、按reserve；未知消费/源锁/owned cleanup异常停新派发；copy失败只重试copy，不重新执行机器人；每族archive全过才进入下一族。范围内自治执行，不逐helper询问。
