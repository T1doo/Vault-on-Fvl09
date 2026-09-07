# F2-inside：最小精确几何修订提案，等待明确决定

本文件仅为影响审查，不修改 verifier、资产、碰撞体、参数或历史结果；0 GPU。

## 已查清的原因

不是“盒子整体不可达”，也不是当前 GPU/坐标变换故障。

1. `lower_y=0.02176539531350136` 可原样重算：官方 box2 collision GLB 的节点变换与0.1缩放 →1mm中心线自由区采样得到 `raw_lower_y=0.01676539531350136` →每一面人工内缩5mm。它不是实测内底面高度。
2. 来源依次为 `f2_asset_geometry_layout_v3._collision_geometry/_cavity_proposal`、`f2_dynamic_search_contract_v3._strict_cavity_from_inside_evidence`；历史 `runtime_v3_2_contracts.py` 已冻结同值，日志§108/§110记录5mm/side选择。§183又把这套 strict cavity 与真实支撑同时保留到最终V10。
3. 15个现场native凸包与对应GLB bounds最大差仅9.47µm；box local Y在当前姿态恰为world Z。因此不是毫米级缩放/迁移frame错误。
4. 独立逐凸包LP证明整个冻结strict cavity与所有box材料不相交。其内一个真实几何体无法获得几何接触支撑。PhysX contact-offset带不等同稳定承重，不能据此伪造pass。
5. can0 metadata横向尺寸约71.15mm，而native collision约50.79mm、visual约49.10mm。当前 `_actor_local_geometry_bounds` 读取metadata，所以每侧额外约10.18mm空包络也进入inside OBB判定。V5所谓runtime一致性核对的是这个metadata getter，不是native碰撞表面相同。

原controlled终点悬空。仅沿原姿态下移，首次native接触发生在约20.571mm下方、`box__9`；原strict OBB的local y_min仅0.00710053，低于冻结下界14.66486mm。原planner5/5不能证明任何物理支撑成功。

证据：`anatomy.json`、`cavity_lineage.json`、`regression.json`，均保存来源/参数或hash。

## 最小组合比较（均未采纳）

| 几何定义 | 已保存首接触姿态 |
|---|---|
| 原metadata OBB + 原六面5mm内缩 | fail |
| 仅改native OBB，仍六面5mm内缩 | fail |
| 仅用未内缩raw区，仍metadata OBB | fail |
| native OBB + 未内缩raw区 | CPU假设性pass，但不能直接采用整个raw区 |
| **native OBB + 仅底面取消inset，侧壁/顶面仍原5mm** | **新增CPU假设性pass；侧壁与顶面负例仍拒绝** |

最后一项只是隔离原因的回归，不是建议取消侧壁/顶面安全边界。

建议最小未来版本为：

- **侧壁X/Z上下界及顶面Y上界仍保留原5mm保守边界。**
- 罐体几何使用经scale、局部姿态与可见/碰撞几何覆盖核对的native包络，修正metadata多余空包络；不得把真实可见部分缩掉。
- **仅底面不再使用“必须离物理底面留5mm空隙”的最终成功语义。** 改为真实、分片floor接触边界：native can不穿入box材料；只允许已标识的承托floor形状接触；侧壁/顶面与机器人碰撞检查全保留。
- 不能把floor换成单一粗略水平面。实际box有7个低floor片与8个侧壁片，首接触为box__9，局部底面有台阶/斜面。须绑定真实shape身份、contact点/法向/分离量与native几何；不能按整个box actor全局忽略。
- 原50帧support、ReleaseSafetyGateV10、慢开爪、250帧settle、最终稳定速度/角速度、真实连续支撑、完全开爪和arm-rest阈值全部保留。

该组合在已保存接触姿态上保持侧壁/顶面界限有充足余量；但完整新floor谓词及真实物理稳定性尚未实现/验证。不能将CPU接触位置直接记为成功轨迹。

## 哪些是修复，哪些是语义改变

- 复算scale/frame、区分metadata/native/visual、补真实shape身份及出处：审计/数值与元数据修复，不改变Gate。
- 更换inside所用几何包络：修正错误的保守metadata，但会改变现有verifier输入和pass集合，必须版本化审查，不能偷偷当作同一verifier。
- 允许真实floor接触替代底面5mm空隙：**明确改变冻结inside几何成功语义**。即便科学任务仍是`box+inside`、物理阈值不变，也不在“普通持续修复”的自动授权范围内。
- 不增加物理垫块、不修改collision mesh来迎合旧谓词；不改变F2三bundle、同物体、同current、动作流、R或split规则。

## 是否可直接换接触区或旧候选资产

当前strict体积与box材料完全分离，且native can包含于旧metadata OBB，所以仅换同盒中的接触区不能解决几何矛盾。旧66个asset certificates只有静态几何资格，`runtime_qualified_pair_count=0`；不存在已证明“支持+strict-inside”通过的替代资产可直接采用。另选资产需要新的独立几何/物理资格，不应随机试多个盒子以掩盖定义问题。

## 明确批准后才做的工作

1. 新版本独立inside几何合同、verifier与support-shape certificate；旧源码/Stage0/失败receipt全保留。
2. 双版本CPU回归：原失败仍按原规则fail；新规则应只修复合法floor支持，侧壁外、顶面外、穿透、浮空、假接触、错shape、错frame/scale均fail。
3. 不重新采已完成F1/F4；F2新版本全部三关系同current重核，旧inside5/5不继承。原公共prefix若证明source/current/anchor兼容可作为新版本候选证据，不能自动接受root。
4. 仅在源锁、有限预算及Guard完整后，使用当前Goal剩余额度做新版本受控inside资格；原子三关系root与真实采集继续依赖其完整Gates。
5. 更新统一readiness和版本边界，不开启formal360/训练/H-reveal/compression/π0.5。

## 建议的精确批准措辞

> 我明确批准未来F2-inside采用一个新版本几何成功定义：修正metadata OBB为经审计的真实native包络，保持原侧壁及顶面5mm安全边界，仅将底面5mm悬空要求改为真实floor支撑接触边界；不得改碰撞体或添加垫块，不放宽原物理接触/稳定/释放/rest阈值。保留所有旧失败和旧verifier结果，在现有Goal剩余预算内先做完整CPU正负回归，再签有限新版本inside资格；不据此直接接受完整F2 root，不授权formal或训练。

在收到针对该语义例外的明确决定之前，inside新物理执行和完整F2 root接受保持关闭。prefix/on/beside可继续独立、不越界的工作。

## 补充：仅底面变更的精确回归已完成

`floor_only_regression.json`（receipt `58c0924cdbc3f1f2c963c7b6883cc29e45dc7f4013c7d237236a3942b02e6528`）只把假设性底面lower_y从0.0217653953改为原raw-grid下界0.0167653953，其余五个界限逐值不变；使用同一已审计native首接触姿态和native包络。

- 几何兼容性通过；X两侧余量52.60/52.61mm，Z两侧29.82/29.80mm，顶面36.68mm。
- 超出X侧壁、Z侧壁或顶面1mm的三个负例全部拒绝。
- 首接触仍是既有低floor片box__9，没有删除或移动任何侧壁/碰撞体。
- 这是**决策用的数值代理回归，不是新验收实现**。未来实际floor规则仍必须使用真实分片native表面、shape/contact身份与不穿透条件，不能把中心线raw-grid平面当成整个底面的真值。
- 真实支撑稳定、浮空假接触、向floor材料内穿透、错shape/frame/scale等完整回归仍在明确批准后实施；本次没有实际物理Gate执行，更没有重判旧失败。
