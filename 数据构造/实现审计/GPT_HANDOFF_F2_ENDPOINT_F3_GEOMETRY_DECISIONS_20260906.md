# F2 端点诊断、F3 实际几何裁决：2026-09-06 完整反馈

本轮输入：https://chatgpt.com/s/t_6a9ce5b770bc81919311cc0f1407c53e 。完整正文13,461字符、含结尾YAML，未发现Markdown下载附件。归档 `EXTERNAL_REVIEW_F2_F3_EXECUTION_FOCUS_20260906.md`；父授权receipt `46c42f0470fcf5be8bb34c619606c7a4d4d5b4f72827eaae13a899eec10ac09d` 未改变。

## 先给结论

- 本轮不是只交helper/tests：F2真正完成15个固定IK问题；F3真正完成两个候选、五状态、两个实际solver实例的40次新旧constraint检查。
- **F2尚未修好**：C能解，U/D在K0也未解，限定yaw也未解；继续换hub缺乏依据。提交一个100mm向内移动stand+beside目标的新布局提案。
- **F3旧抓取终点确实不合法**：手掌/夹指与桌面或垫子交叠，不是单纯瓶子抓不稳。旧micro条件不满足；提交原recipe派生的top-down新抓取CPU提案，不能重跑旧终点。
- F1/F4已完成9条变体不重开。开发接受仍6root/27raw；18个pilot候选格重新只读核验通过，但Stage1仍0/48、formal仍0/360。F2/F3尚无完整接受开发root。

## F2：实际约束矩阵

执行目录：`/nfs_share/lijunhui/Robotwin2/datasets/f2_endpoint_constraint_remaining_v1_1`。

| 目标 | K0：仅关节限制 | K1：加self | K2：加环境 |
|---|---:|---:|---:|
| C，当前持物姿态 | 7个全约束有效解 | 9个 | 7个 |
| U，目标上方 | 0 | 0 | 0 |
| D，放置终点 | 0 | 0 | 0 |

数字是每个问题32个返回解中，额外通过FK及全部三套约束交叉检查的数量，不是只读solver.success。C三个问题原始solver.success分别25/9/7，所以没有假设约束增加时求解成功必定单调。

固定+90/-90/180 yaw的U/D共6题也全部0全有效解。合计9+6=15IK问题；没有完整端点对，未调用U/D/U/N的条件4条trajectory query。0物理执行、0新raw/root。

原K0 U最佳位置残差40.16mm、D38.94mm，对应解姿态亦未达标。C_K2最佳位置残差约0.00061mm。这说明有限预算下问题不能仅用环境碰撞解释，但**不是数学不可达证明**：迭代求解失败仍可能受优化局部极值影响。按决定停止追加seed/yaw/hub搜索。

模型落实：

- 保留锁定 `Robot._trans_from_gripper_to_endlink → world/base → frame_bias → Aloha rotation` 完整目标链；名字映射关节并保留原5位round。
- 固定32seed、同一实际Halton seed bank、100迭代、5mm position和原quaternion-vector 0.05判据。后者是sin(角度/2)形式指标，不错误标成0.05rad；同时报告实际角度。
- K0实际关闭self/world优化与约束，K1关闭world，K2加载actual MESH环境；逐rollout enabled/weight、Warp顶点/faces/pose/enabled及实际link FK均检查。
- 手持can使用实际native shape拟合为fl_link6附着的机器人碰撞球，不作静态世界障碍。正常夹持忽略link6/7/8，其他self/world保留。模型球近似与配置膨胀不冒充精确物理不可能；每题首解和所有全有效解记录最近sphere-world pair距离。

首次scene在0IK时因原YAML `extra_links:null` 与dict.setdefault用法失败；新V1.1显式归一化None、补CPU回归，使用既有2scene许可中剩余一个。旧V1与失败回执保留，累计**2scene/15IK/0trajectory/0physical**。没有第三scene授权。

### 唯一F2后续提案

`F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json`：沿beside目标指向已知可达的当前持物geometry centre，一次推导100mm平移，world XY为`[-0.0996618812,-0.0082164127]`；stand和目标一起移动，保持relative beside、upright/yaw和抓取关系。

原target centre `[0.08,0.07]` → 新 `[-0.0196618812,0.0617835873]`。位移量是按K0残差量级取整的设计启发式，不是IK证明。`F2_INWARD_PROPOSAL_CPU_GEOMETRY_V1_20260906.json`用实际native mesh确认与box/scale/wall不交叠，尚不证明全臂路径或table footprint有效。

这会改变当前布局，因此必须新root/current/candidate lineage；不能修改旧current或把原inside5/5自动宣布适用于新scene。原inside5/5保留，不重跑旧11-query gate。请审查此单一布局版本及其下一步有限端点/qualification条件，不再批旧hub搜索。

## F3：模型通过，但旧终点被实际几何否决

执行目录：`/nfs_share/lijunhui/Robotwin2/datasets/f3_zero_scene_solver_replay_v1`。

- r3063/asset13：initial、pregrasp通过；原末端fl_link6穿pad，fl_link7穿table/pad。正vertex penetration witness约4.10/14.28/4.96mm。
- r1401/asset5：initial、pregrasp通过；原末端fl_link7穿table/pad，witness约5.26/4.49mm。
- 这些数是实际交叠见证，不是全局最小分离位移。原始FCL结果、physical collision filters与contact offset分别记录；未把负distance sentinel当深度，也未把contact offset本身当物理冲量。
- 两个候选的actual model FK、known-clear不全拒绝均通过；实际motion_gen和motion_gen_batch都生效。最终均`EXACT_ENDPOINT_GEOMETRY_INVALID_NO_PHYSICAL`，不能再运行原微执行。

途中两次真实基础设施失败完整保留：

1. 首scene导出多shape时重复name，CuRobo按name缓存导致实际Warp mesh不符；严格检查阻断。修正为body内唯一shape名，旧有效local vertices/faces保留。
2. 剩余scene通过initial实际FK/clear检查，但切换状态时CuRobo0.7.8 `JointState.copy_` 在v/a为None时返回clone，上层没接回，锁定手指metadata残留。CPU复现后使用隔离兼容层显式同步各rollout命名locked-position，不改安装库。

随后用已捕获geometry+旧trace作**零新SAPIEN Scene** solver replay。URDF CPU FK对两条trace全部814+644状态、左右臂对齐，最大位置误差约3.99e-7m；native asset13 cooking先逐顶点/faces匹配原live capture，再同API读asset5。实际configured fl_base_link定义环境坐标；legacy目标经验校正单独保留。没有通过创建第三scene绕过预算。

累计2non-action scene；40次模型检查完成；任务trajectory query0、physical attempt0。原余6query/2physical是条件许可，**旧endpoint Gate为false，不可花在重跑旧终点上**。

### F3几何新recipe提案

`F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json`：两个父recipe各一个解析方案，无候选网格搜索。瓶长轴table-Y，夹爪闭合方向X，approach为-Z，保留原抓取纵向站点；按实际hand最低点、pad顶面推导17.31/10.89mm抬升，提出8mm几何余量。开爪真实shape对table/pad/bottle检查均无确定穿入。

这**仅是CPU终点几何提案**。实际flange world pose不是可直接送入旧接口的reported goal；仍需逆向校准并复核完整legacy目标链、真实开爪IK/末端约束、全臂路径、闭合后接触保持、旧完整窗口Gate与原25mm lift/20mm rise/50frame postlift检查。没有放宽原Gate，没有物理weld，没有shared-V/no-suffix/raw/root。请审查新recipe，而非重复授权旧micro。

## 辅助交付

`PILOT_18_CELL_ELIGIBILITY_READONLY_RECHECK_V1_20260906.json`：18行raw/video/verifier/current/anchor/root/matrix复核，与旧final audit逐行相同，F4六条跨realization final-state equivalence仍通过；不自动promotion。

`F4_PILOT_B_NEW_LAYOUT_CPU_PROPOSAL_V1_20260906.json`：真正新root，seed2026090604、A/B/C source和slot整体table-X负向10mm，common-X tray不改；不能换名复用A current/anchor/prefix/controls。原三程序block transition/sweep CPU几何检查通过，机器人IK/路径/物理尚未验证。目标3r_pc+3r_inv_motion。

`F4_PILOT_B_PROSPECTIVE_BUDGET_V1_20260906.json`：仅预算附案，按原r_pc生命周期11scene/136query加3motion scene推导14scene/136query/6raw/1root、32400s；须落实新runner和前置Gate账本后另审，不能拿这份proposal启动GPU。新增前置probe若必要，必须在执行前另行计入预算。

若后来Stage1获准，结构缺口仍F2-A/B12 + F3-A/B12 + F4-B6 =30格；已有18格只是候选证据。这不是“已经完成18/48授权采集”。

## GPU、版本与机器证据

本轮所有GPU job串行，均fresh-idle physical GPU0，UUID `GPU-2c620e6c-9639-2022-b573-9847dfa33769`；每个manifest允许范围仍完整GPU0–7，不是GPU0-only。

| job | Guard / child PID | 耗时 | 终端 |
|---|---|---:|---|
| F3首次模型scene | 2400063 / 2400125 | 55.03s | cache命名检查失败，清理通过 |
| F3剩余模型scene | 2460802 / 2460833 | 63.53s | locked finger metadata检查失败，清理通过 |
| F3零scene replay | 2525988 / 2526015 | 35.84s | 40/40检查完成，两个旧终点不合法 |
| F2首次scene | 2551951 / 2551974 | 53.83s | None配置错误、0query，清理通过 |
| F2剩余scene | 2558608 / 2558636 | 93.45s | 15IK完整负结果，清理通过 |

每个job都有UUID/lease/pre-launch/post/cleanup；独立host post均GPU0=14MiB/0%/P8/no compute，所列任务PID退出。所有历史失败、stdout/stderr和模型/问题回执由`ENDPOINT_MODEL_COMPLETED_PUBLICATION_V1_20260906.json`绑定文件hash。

官方RoboTwin仍tracked clean `c3ddfa8b97d5519efa828b075999bd0006778e5e`；active controlled source仍`3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7`。新模型修正只在Vault隔离runtime；F1父源9873bbe…和F4 active源保持分开。所有新JSON显式UTF-8/原子exclusive写入。

统一机器状态：`STAGE1_READINESS_AFTER_ENDPOINT_MODEL_DIAGNOSIS_20260906.json`；追加日志§485–§494。Stage0不重开；Stage1、formal360、训练、H-reveal、compression、π0.5仍未授权。

## 请下一次审查具体决定

1. F2：是否接受唯一inward布局方向，并给新scene/目标的有限endpoint与整体qualification入口；保留原inside证据，禁止旧hub无限重试。
2. F3：审查两份原recipe派生top-down几何方案，先确认actual/reported goal映射、开闭爪与全臂约束，再限定新recipe micro预算；原micro不重跑。
3. F4-B：可单独审查真实新布局与6条pilot-B结构，但当前CPU预算附案不是GPU授权。
4. 不重复审批已完成F1/F4九条、不把18候选格直接认作Stage1接受、不越过数据资格启动机制训练。
