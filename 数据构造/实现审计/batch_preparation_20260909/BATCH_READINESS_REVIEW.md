# 四族生产准备度审查

基线：31a0287a976371f490baa1d0e7ca5ecd9cea3fcd。依据用户2026-09-09最新审阅；只做CPU准备，P4采集完成状态保留。此审查不将已有pilot升级为正式数据。

| 族 | 真实证明 TEMPLATE_VERIFIED | CPU_BATCH_ENTRY_READY | FIRST_WAVE_PHYSICS_PENDING | BATCH_REPEATABILITY_VERIFIED |
|---|---|---|---|---|
| F1 | 三对象选一与历史path/motion运行、跨目录验收 | 否：正式九条统一入口未接通 | 是 | 否 |
| F2 | P4 A/B各六条，真实inside/on/旁放及变体 | 否：四个固定ID、六条finalizer | 是 | 否 |
| F3 | A六条兼容保留，B六条独立验收，竖瓶V/H/rest | 否：同上，新增场景尚无qualification | 是 | 否 |
| F4 | common X、三种顺序与变体的历史成功证据 | 否：开发profile与特定qualified布局绑定 | 是 | 否 |

“否”描述批量入口缺口，不撤销已有物理成功。参数清单工具已实现；该工具不是机器人采集器。

## 实际调用链及最小修改

路径以下相对RoboTwin；引用代码已经读取，不导入GPU模块。

- F1：`f1_batch_generation_pilot_v1.py::_layout`提供固定三位置与identity轮换；`real_sapien_adapter_f1_batch_v1.py::RoboTwinRealSapienF1BatchPilotAdapterV1`继承strict-prefix adapter，按planned display order生成候选，verify明确formal_data=false。必须让scene_layout物理参数真正进入factory，保留candidate display permutation；用正式wrapper接三种realization，调用成熟primitive与raw writer，不把开发false标志直接替换true。验收增加9格完整性、两组各三项变体比较、同rootcurrent/prefix与source锁。
- F2/F3：`redesign_f2_f3_v2/scene_spec.py::scene_spec`只认四ID；`f2_scene.py`、`scene.py::RedesignF3Scene.setup_demo/load_actors`消费A/B固定布局。`collector_v2.py::_f2_cell/_f3_cell/run_root/main`内部再取scene_spec；CLI choices也是四ID。`pilot_contract.py`定义A=pc+path、B=pc+motion。必须新建formal spec接口，逐层显式传同一冻结spec，禁止下层重新按ID生成默认配置。
- `finalizer.py::finalize_root`硬编码len(cells)==6和每program两条，只比较一个alternative；正式wrapper须严格检查3×3唯一键，baseline分别比较path和motion，复用既有cell独立验收、RGB/state/anchor和实际prefix数组核对。`_variant_check`还依赖pilot root_id取冻结变体要求，需改为接受正式contract中的要求。
- F2参数必须贯穿target、scene、verifier：保留v5与side_then_geometry_target；A lift历史0.16m配置、B逐cell0.12m来源分开，不能一律退回默认高位路线。支持面从collision mesh推导，box top .855m等由构造几何生成。尺寸和抓取方案首波冻结。
- F3 `scene.py`只接受A/B；rest、work center、瓶/pad需spec驱动；保留table-frame ±z/±x、0.047m事件指令和B time_scale=1.5的来源，不将某程序绑定不同速度。新增root须九条共用首V、rest、场景与候选。
- F4：`real_sapien_adapter_f4_qualified_root_v1.py::RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter`要求三个full_program_specs的candidate/isolation/legacy场景hash一致；`f4_full_program_physical_v1.py`为后缀plan/execute。它依赖既有qualification，不可将新布局冒充旧qualified布局。最小扩展为新spec生成full_program_specs及有限资格，保留对象slot映射、原执行臂调度和neutral终态。motion参考`goal_pilot48_v1/f4_b_motion_runtime_v2/`成功profile，不能调用F2/F3 collector代替。
- 各族恢复：使用冻结spec/source版本/current/prefix身份及磁盘独立验收确认可复用cell；只补未完成格。共享记录/入口错误停批，正常不可行进入有序reserve；来源/预算/自有资源异常停新派发。保留实际计量与失败分母。不要重写Guard或ledger。
- 数据出口：F2/F3已有observations.read_bundle/model_envelopes；formal wrapper要把raw占位行剔除一次，inputs/supervision/audit隔离。新增portable工具只支持本轮明确的单cell验证，不称为全族生产归档器。

## F1-red定向核对

`F1_SOURCE_LINK.json`七项通过：九变体总审计记录的root SHA、root_finalization.accepted、parent_root、trace、video、原provisional SHA与raw manifest文件绑定均一致。最终root在`cmf_realization_unattempted8_v1_3/F1_A_path/root_receipt.json`，明确内嵌恢复目录F1-red分支及receipt_recovery。原provisional本身为截断JSON，不冒充可解析最终回执。完整汇总已覆盖该trace；本轮追加映射，未补造原目录root、未改旧索引或旧raw。

## 不阻塞首批的后续扩展

换瓶型/尺寸、强光照、复杂障碍、跨设施relation解耦、模型训练与高清均延期。首批仍须满足canonical角色数和split难度：现有简化F2/F3模板不自动证明6–10角色、crowded投影及干扰物门；需要在正式scene builder中补齐规范角色并做资格，不能标为已经验证。

当前24格来源清单把v43放在各cell的source profile中，实际应理解为收口参考源。正式准备必须从原job manifest/source锁解析执行版本；F3-A是早于v43的P3来源，不能拿v43冒充采集时源码。本轮单cell包用于离线读取，重仿真能力未验证。
