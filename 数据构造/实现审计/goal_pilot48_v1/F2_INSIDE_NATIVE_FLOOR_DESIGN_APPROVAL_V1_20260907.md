# F2-inside 原生几何与箱底支撑：用户明确批准的窄范围设计修订

决策ID：`F2_INSIDE_NATIVE_FLOOR_GEOMETRY_DESIGN_V1_20260907`。

父任务：`cmf_pilot48_20260907`，父合同与累计预算不重置。

## 授权依据

主线程向用户明确询问：是否采用经审计的原生几何包络，仅取消箱底方向5mm内缩，侧壁和顶面边界不变，仍要求真实支撑、慢释放、稳定、无穿透；旧版本/失败保留，新版本独立验证。

用户直接回复：**“允许允许，你把改动记录清楚就好”**。

该回复批准的是上述F2-inside几何成功定义修订，不是泛化的verifier放宽许可，也不是独立GPT外审。详细影响依据为 `f2_controlled_suffix_runtime_v1/INSIDE_GEOMETRY_DECISION_REQUEST.md` 及其解剖/来源/回归证据。

## 新旧对照

| 项目 | 原版本 | 批准的新版本范围 |
| --- | --- | --- |
| 罐体几何 | 保守metadata OBB，横向约71.15mm | 经scale/frame及可见/碰撞覆盖审计的native包络；不缩掉实际可见物体 |
| 箱底边界 | free-grid底界再内缩5mm，与真实箱底支撑冲突 | 基于真实分片floor、接触身份及无穿透的支撑边界；不得把raw-grid平面直接当真底面 |
| 侧壁与顶面 | 原5mm保守边界 | 五个边界原值不变 |
| 支撑、释放、稳定、rest | 原物理标准 | 50帧支撑、慢开爪、250帧settle及其余原数值门全部保持 |
| 资产/碰撞体 | 当前真实box/can资产 | 不改碰撞体，不添加垫块，不全局关闭box或侧壁 |
| 旧失败 | 原verifier判定失败 | 保持失败及原始字节，不能回溯升级成功 |

这会改变未来F2-inside verifier的几何输入和成功集合，因此必须使用独立设计/实现/verifier版本与源锁，不能冒称原verifier未变。父合同禁止任意物理阈值变化的规则继续有效；本文件仅记录此项已获明确批准的几何定义例外。

## 执行与验收约束

1. 先完成双版本CPU回归与影响清单：合法真实floor支撑正例，以及侧壁/顶面越界、浮空、穿透、假接触、错shape、错frame/scale反例。决策用接触姿态不是成功轨迹。
2. 明确区分实际7个floor片和8个侧壁片，保留所有机器人/非支撑碰撞检查；不能按整个box actor统一忽略。
3. 再由主线程在现有Goal剩余预算内，创建新ID、新manifest与新输出进行有限GPU/物理资格。全部Guard/UUID/lease/fresh-idle/pre-post/cleanup要求不变。
4. 新布局inside/on/beside仍必须同current/anchor、候选宇宙与来源一致。旧inside planner5/5、静态几何或单次支撑不能自动接受完整F2 root。
5. 记录每次实现变化、命令、源/输入hash、失败和新版本结果；统一readiness保持事实区分。

F1/F3/F4规则、Stage0封存、formal360执行、训练、H-reveal、compression和π0.5边界均不因此改变。canonical《数据构造方案》保持原字节，本批准作为后续窄范围设计覆盖单独保存。
