# 已授权竖直资格：CPU择一冻结B，尚未GPU

依据新用户授权 `USER_F2_CONTACT_F3_UPRIGHT_APPROVAL_V1_20260907.md`，先读全最新版AGENTS和批准范围。当前选择严格在GPU前完成，未修改旧三次配方/失败，也未触碰在跑的F2源。

## A先审但不能声称承托

原提案A固定颈部站点local-y=.220、正常指尖接近深度.140m。原生24次二分只求**几何首次闭合接触**，不是24个规划或物理候选。两指首触均为cap片bottle__2，local-y=.225314/.225433m、法向几乎水平；不是颈区夹持，更没有凸缘底面向上承托。因必要条件失败，A未冻结、未物理尝试；不能把“都碰到瓶盖”包装成形封闭成功。

## 唯一冻结B

按授权仅CPU转审B上段直壁。冻结 `design_spec.json`，receipt `1976ee32ab6d53fc6bfdfe2ed949c70614c96cfb7d61529d6014127a0b05436f`：

- asset13、scale0.132、质量设置.01、摩擦/惯量/native片/夹指不改。
- 瓶actor nominal pose `[-.18,-.06,.75,√.5,√.5,0,0]`，local+Y竖为world+Z。
- B名义grasp `[-.18,-.20,.92,√.5,0,0,√.5]`；侧向+Y接近，pregrasp为y=−.32、其余不变，间距12cm。
- 唯一seed=2026090713。实际settle姿态通过原数值门后，以同一个冻结bottle-relative变换派生两目标，不搜候选或重采seed。
- 两指几何首触同一连续瓶身片bottle__4，q约.033908/.033712m，均能从原open到close.50范围接触。真正接触高度local-y≈.159536，比真实COM高约49.085mm；不是拿名义站点.170直接声称高59.55mm。
- 五档闭合无掌/瓶或手/pad/table相交，open pose无提前触瓶；原Robot工具/world/bias/Aloha入口往返通过。

B是COM下置的摩擦侧夹，不主张凸缘承托或已证稳定。只能物理验证这一冻结设计；失败后不得再物理换A、变高度或补第三scene。

## 支撑、全臂和剩余缺口如实保留

名义native底部与原pad顶面.75解析对齐，瓶体最高约.997888m。底部并非已证明共面平底：此前1µm层只有1点，0.1mm层2点，不能据CPU说竖直站稳。第一次fresh scene必须在固定60步settle后、任何IK/抓取前过真实支撑和原稳定门，失败即止。

实际历史initial q的左右16个臂link（fl/fr1..8）及106组非相邻self对、table/pad/新upright瓶检查均无相交。左右native形状逐link经URDF描述相同证明再映射。没有捕获base/wheel形状，不冒称整机器人完整碰撞自由；新目标尚无完整q/规划轨迹，不能拿hand pose几何替代目标全臂IK或真实路径。后续live资格必须在3次IK中检查实际全臂native解，并对所有真实计划controls执行前检查，至少保留已知fl3/fl5，新增朝向需补base/其它非邻接覆盖。

`expected_mass_properties`保留真实旧质量记录作为来源；其中com_world属于历史姿态，**不会**被新initial_gate比较为新世界COM。只比较mass_kg、principal_inertia和cmass_local_pose三个本体属性；当前world COM由新实际actor pose计算。没有复制旧world位置为竖直期望。

## 新CPU接口（不是可直接签GPU的完整runner）

`scene.make_scene_class`以私有globals替换旧F3 actor创建时的pose，asset/scale/质量逻辑保持；不先创建横放actor再进行未计账物理复位，不改全局SCENES或旧类。

`initial_gate`使用旧BOTTLE_POSITION_ATOL=10mm、ORIENTATION=.2rad、fixture1µm/1µrad及原runtime速度门，另外核验新seed/真实scene identity/60settle/质量惯量。`derive_targets`只应用冻结relative pose。

`qualification_entry.qualify_existing_scene`提供必须注入live ports的严格顺序：standing→current/anchor/trace→C/pregrasp/grasp三个single full-constraint IK→原三计划micro→先落micro pass；条件第二scene在此前同spec全部通过后才接原11计划prefix扩展。局部失败保留实际小于上限的query，不能假报满额。micro成功必须携带原postlift、完整world恢复两路valid和full-native controls证据。

这些ports、完整guarded scene context、实际GPU模型/IK及全臂计划前筛查仍需接线/审查；`execution_ready=false`明确阻止把CPU接口当可直接运行作业。当前未创建Scene、solver、manifest或预算。

预算保持第一次6solver/1scene，只有通过才第二17solver/1scene，合计23/2scene/2action/0collection/3060lease；同一新轮次计入原Goal，旧3次上限不重置。close.50/hold250/lift25/原20mm5mm.05rad50帧、F3三个程序/table-frameV/H/250Hz均不改。

新current/anchor、prefix hash/回放、upright return/release与observable task-tree来源以后另行核验；不继承旧current/prefix或接受根数据。这一有限资格本身不产生完整F3root/正式数据。
