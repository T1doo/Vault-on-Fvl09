# F1 strict-prefix root revision-1 failure report

## 裁决

`F1 revision-1 = failed_planner`。不是 accepted root，也不是 Stage 0 数据。

红、绿 suffix 的10个链式planner segments全部通过；蓝色的pregrasp、grasp、4 cm lift、累计8 cm lift均通过，但第5段`safe_vertical`从当前约0.9614 m继续升到EEF z=1.02 m时失败。系统因此在三分支真实suffix execution前fail-closed。

| Role | 记录内planner | 结果 | 终止点 |
|---|---:|---|---|
| red | 10/10 | passed | rest |
| green | 10/10 | passed | rest |
| blue | 4/5 | failed | `safe_vertical` |

Blue失败goal：

```text
[-0.0200014388, 0.0080226472, 1.02,
  0.5243617622, -0.4743934205, 0.4743877970, 0.5243585061]
```

失败segment的start/end qpos SHA均为`6187143e8d5c…ddf1d`，说明planner失败后没有推进。

## 公共前缀与安全性

- canonical prefix：793 steps，action SHA=`22f8c7c2…95069`；
- 三个fresh suffix scenes：current、start anchor、prefix bytes、prefix-end qpos与semantic/acceptance anchor等价；replay planner delta=0；prefix中target role不可见；
- recorded planner=`1 prefix + 10 red + 10 green + 5 blue = 26/64`；
- branch suffix execution=`0/3`，recovery=`0`；canonical-prefix reference另有1次真实物理执行，不能混称为整次运行0动作；
- 8/8 scenes cleanup与monitor restoration通过，orphan=0；
- Guard child exit=1对应受控planner failure，非timeout；GPU0 pre/post均14 MiB、0%、无compute，release verified。

## 新发现的planner审计缺口

Revision-1的26只统计了显式segment planner。官方`choose_grasp_pose()`对每个procedural cube的4个contact points各调用一次`left_plan_multi_path`，每批含10个pose candidates；三色合计还有12个未入账batch API calls／120个内部candidate slots。

因此posthoc完整API-call口径为`38`，仍低于64，但revision-1机器budget receipt的26是不完整计数。该缺口不改变本次失败终态；它必须在任何下一root前修复，不能把26继续表述成所有planner调用。

## 下一停止线

F1 revision-1已永久消费。只剩一次source-distinct revision-2；必须保持同slot、seed、scene layout、left arm、RGB roles、plasticbox/base3、candidate universe、canonical prefix和verifier。Revision-2任一planner或semantic branch失败后F1即terminal incomplete，不允许revision-3。

证据namespace：

```text
数据构造/实现审计/probe_outputs/
nonformal_runtime_v3_3_f1_strict_prefix_root_seed20260829_revision1_run1/
```
