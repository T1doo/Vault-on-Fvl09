# F4 final uniform layout impact review v8

状态：`cpu_geometry_pass_final_real_ik_pending`。

Layout-v3证明right x-band本身不足：三对象在y=0.175仍全部pregrasp失败。最后repair保持x-band与全部任务语义，只把整个object row统一移到y=0.02，并把三个visible slots统一移到y=0.16：

| Role | Object xy | Slot xy |
|---|---|---|
| A | (0.16, 0.02) | (0.15, 0.16) |
| B | (0.28, 0.02) | (0.30, 0.16) |
| C | (0.40, 0.02) | (0.41, 0.16) |

保持不变：common-X、official tray/base0、right arm、cube grasp transform、pregrasp distance、neutral、ABC/ACB/BAC、object-slot mapping和verifier。

Layout=`f4_right_arm_workspace_base0_v4_final`，SHA=`d8abbdd62885a814b2eeaa57cb4b9802591b47acea753f02b8014dccfb79dc85`。CPU checks全部通过：objects/slots/table/tray/common间距有效；objects最小间距0.12 m，slots约0.11 m。

这是F4最后一个implementation repair。下一次A/B/C no-action IK若不是3/3通过，立即标记F4 terminal，禁止staged及ABC/ACB/BAC，不再移动layout或修改抓取姿态。
