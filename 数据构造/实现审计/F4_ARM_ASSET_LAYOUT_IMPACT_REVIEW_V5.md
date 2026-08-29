# F4 arm × asset × layout impact review v5

## Selection

```yaml
layout_version: f4_right_arm_mirror_base0_v1
arm: right
tray: 008_tray/base0
tray_pose: [0.28, -0.12, 0.76]
common_X_pose: [0.28, 0.10, 0.762]
objects_x: [0.07, -0.08, -0.23]
objects_y: 0.08
slots_x: [0.07, -0.08, -0.23]
slots_y: -0.18
branch_neutral_xyz: [0.15, -0.02, 0.95]
```

四个官方tray IDs均完成model-data/visual/collision provenance审计；base0具有最小footprint，因此按预注册排序优先。该right-arm layout满足tray完整位于table、tray不遮挡objects/slots、objects和slots各自≥10cm间距、三个program共用同一arm/layout，且位置不编码ABC/ACB/BAC标签。

首次机器JSON写入因NumPy bool失败，未生成artifact；修正全部checks为Python bool并增加整份review序列化测试后成功生成。

当前状态：CPU geometry pass；head/wrist实际可见性与right-arm real planner preflight仍待一次有限GPU scope验证。只有preflight通过才可执行common-X和后续自然程序。
