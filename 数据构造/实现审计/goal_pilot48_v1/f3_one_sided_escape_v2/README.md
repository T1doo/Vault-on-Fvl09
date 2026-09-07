# Model-eligibility revision2：one-sided native unloading

独立目录 `f3_one_sided_escape_v2` 与 `f3_runtime_v6`；旧tangent V1/v5、旧支持门和全部失败未修改。主线程已采纳one-sided设计，但本交付只有CPU实现和源锁，无GPU、reserve或新manifest。稳定recipe revision3、route revision2、25mm lift、原postlift和2fresh成功要求不变。

## 唯一方向性变更

新schema `stable_grasp_one_sided_native_unloading_escape_v2`。全250帧native gap使用 `g >= -0.0001m`；负向epsilon仍原0.1mm，不提高为120µm。任意正向上界去除，因为它曾把安全离开pad方向拒绝。模型适用性revision明确=2，positive_gap_upper_bound_m必须None，试图增加负向epsilon或重新凑正阈值均拒绝。

这不等于允许任意场景忽略pad。仍必须当前实际full single/batch因world collision拒绝，全部负sphere非空且只属attached瓶/同一pad；同pad至少一次真实支持、table/其它支持0；原250双指/selected接触、信号完整、forbidden0、原5mm/.05rad抓持稳定性和250Hz全部保留。旧支持整体predicate真实重算并False，完整旧witness保留且与新证书hold/pair逐项一致，旧pair摘要True必须与实际列表相容。

若fullworld已有效或当前负pair为空，证书拒绝；不能靠把gap说成正向安全而申请不必要例外。新schema不能接受旧V1证书，旧V1也不会因新代码而通过。保存001原失败在回归中始终False；另一次仅内存改变schema的counterfactual验证展示方向性影响，不写成fresh证书或GPU结果。

## 其余完整性/物理边界原样保留

- actual scene identity/job、完整命名qpos、actor/EEF/抓持变换、原帧/时间/native/world/config哈希绑定。
- factory在CUDA构造前验证world/config；native执行前验证native/world/qpos/actor/EEF精确未变。
- 构造前绑定四入口mask，真实single/batch缓存/所有cached回调及full/pair状态比对接口；robot/pad/table/其它碰撞约束不变。
- 单scene、单固定25mm向上目标、单plan lease，过期/变world/重用即拒绝。所有实际控制保留native fl3/fl5和native不深入/下包络不下降/最终离支撑检查，离散检查不冒称连续证明。
- 原postlift Gate与finally fullworld恢复；恢复必须恰single/batch两键且valid严格True才可继续。原错误与恢复错误分别保留。
- 微门局部最多3solver。generic dispatcher测试以kind=F3_MICRO执行，local2/meter3拒绝、3/3通过；以后pureissuer仍须保留该kind，新模型类型另字段说明。

## CPU交付

最终 `CPU_AUDIT_V2_1.json`：43tests通过，包含所有V1硬化测试、正/负108.8µm方向反例、fullvalid/empty-pair拒绝、epsilon/旧pair摘要反例、旧001失败保留、v6生命周期/恢复及真实generic对账。初版41tests的CPU_AUDIT_V2保留历史；最终源锁以V2_1为准。CPU_INPUT_BINDINGS绑定保存006/001真实输入、几何与impact审查。

`test_fresh_input`中实际GPU-state和factory明确是CPU mock；synthetic250只验证原supported分支，不产生数据。所有实际新GPU kernel/factory conformance和新25mm物理效果仍未验证。接下来须单独pureissuer审查/主线程签发，不自动重跑旧V1或创建第四稳定配方。
