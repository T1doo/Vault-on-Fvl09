# F2 mutually exclusive region/layout v2

状态：`cpu_geometry_pass_gpu_suffix_gate_pending`。

冻结联合布局：

```yaml
layout_version: f2_box2_mutually_exclusive_facilities_v2
can_xyz: [-0.28, 0.04, 0.79]
box_xyz: [-0.29, -0.20, 0.78]
scale_xyz: [-0.10, -0.20, 0.77]
stand_xyz: [0.20, -0.03, 0.77]
```

Predicate v2：

- `inside`：plasticbox/base2 true cavity 的 facility-local 区域；
- `on`：electronic-scale top-surface facility-local 区域；
- `beside`：display-stand 0.12–0.23 m annulus，并明确排除 inside/on 区域。

5 mm 网格覆盖 20,091 个桌面点：inside=961、on=784、beside=4,832，三者 overlap count=`0`。三个预注册 beside sector 均在桌面内且不进入 inside/on；scale top 到 stand annulus 也有正几何间隔。

完整常数、candidate points、facility distances 与机器 checks 见同名 JSON。该布局仍需 GPU suffix planner Gate，不是 Stage 0 授权。
