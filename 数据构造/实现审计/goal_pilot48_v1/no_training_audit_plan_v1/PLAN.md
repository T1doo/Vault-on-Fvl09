# Pilot48 无训练审计：覆盖盘点与后续执行方案

状态：**盘点已实施；统一审计方案待执行**。当前只允许已登记pilot，绝不读取formal/test、生成H视图、训练或推断模型。

## 真实证据盘点

`INVENTORY_001.json`本轮读取pilot_cells及24份真实raw manifest，仅核元数据/登记映射，不重算全部大数组或视频内容。当前F1/A、F1/B、F4/A、F4/B各6格，F2/F3各0；不能将未完整的F2 on/beside资格填入raw分母。

|要求|已有真实证据|尚未覆盖/本轮限制|
|---|---|---|
|48格结构、重复raw/trace/rollout、六格同root/current/candidates|pilot_matrix_audit_v1；本轮对实际24格登记重跑通过|48/48未齐；不代替raw物理复核|
|raw/trace/video hash、N/N+1、26维/250Hz|reuse18/audit.json原18及F4-B FINAL_AUDIT_001原6；本轮24个manifest对登记身份一致|本轮不是大数组重验；最终48齐后需同一版本统一执行|
|current三RGB与原始row0、38唯一DOF→76 qpos+qvel|reuse18/current audit和F4-B current恢复，原6存在稍后捕获的显式同hash复用证据|不能把重复两份38DOF算成76关节；也不能称恢复的current在旧root当时已保存|
|严格prefix与fresh replay、失败/资源/cleanup|各root finalizer、reuse18 resolution；F4-B资源resolution与late-release链|“原终端false+追加接受”需保留；free path不要求prefix字节相同|
|F4三程序顺序/六轨迹终态/真实motion变化|F4-B独立原finalizer、顺序、1.10 retiming重算；reuse18有F4-A六轨迹终态|F3无完整pilot；没有Temporal Gate/H-reveal结果|
|负例|已有pipeline/raw/canonical/物理Gate的CPU单测源码|不能声称已有统一24/48真实母轨迹派生负例报告；需显式fixture隔离|
|泄漏字段|raw分区本来保存planner/对象/接触等审计字段；model_view顶层五字段投影与顶层禁键单测|未发现统一最终输入出口审计。build_model_view只浅层检查，允许嵌套path；不证明训练已泄漏（没有训练），但不得当严格类型/递归隔离已完成|
|时间对齐|validate_raw_streams实际验收检查dt=1/250、start=state[:-1]、end=state[1:]，原容差1e-9/1e-12|仍缺统一逐24/48 raw与trace全行effective/action/state映射重算及事件marker边界报告；不能只看metadata frequency=250|

## 执行顺序与明确输出

统一命名新 `no_training_audit_execution_v1`，所有输出write_new UTF8 exclusive、原输入只读；每个步骤单独有限CPU timeout，先冻结source/input hashes。禁止直接调用会覆盖旧审计文件的 `reuse18.audit.run()` CLI。必要时提取其pure检查或传全新报告目录。

1. **S0 冻结输入（120s）**：只遍历accepted_existing/accepted_new，调用pilot_matrix_audit.inspect_document；冻结表及每格manifest/current/trace/raw/video/final receipt路径/sha和合法追加接受链。pending无evidence、formal_data=false、无test路径；24条只报partial，不因存在资格trace增加分母。输出INPUT_LOCK.json、COVERAGE.json。
2. **S1 原始结构/时间（每格180s，总48×180s上限，串行）**：直接调用原verify_raw_artifact_integrity、validate_raw_artifact_contract/validate_raw_streams；重算N26/N+1、全部timestamp有限/原250Hz容差、start/end相邻状态关系；从trace转换原函数重新导出raw streams，逐字段对磁盘array精确比较（仅原浮点转换处沿既有规则，不新增容差）。current使用既有lossless38/76 auditor验证row0；不从未来state抽current。输出每格STRUCTURE_TIME.json及失败明细，不输出RGB或未来视图。
3. **S2 cohort/事件对齐（每root300s）**：r_pc只对named strict-prefix cohort核canonical数组及原P、divergence和fresh replay；r_inv_path/motion另组，仅验证意图/order/current/anchor/真实变化，绝不强迫自由路径prefix一致。事件时间来自trace marker/actual role receipt与step/timestamp映射；边界0≤start≤end≤N，不做任何H切片、task-tree horizon标签或H性能统计。F3/F4只调用冻结的原顺序/终态审计；当前F3记not_available。
4. **S3 无训练负例（单suite120s，CPU内存fixtures）**：下表变更均基于输入锁中的小型元数据或必要局部数组拷贝，保存fixture规则/源hash/预期拒绝码，不写入成功dataset。结构负例必须原validator拒绝；科学语义负例必须原family verifier拒绝，不能用单纯hash不匹配冒充科学语义检查。无可复用pure verifier的项先标pending_interface，不伪造通过或启动模拟器。
5. **S4 泄漏出口（120s，结构fixtures，不生成model-ready H数据）**：审查五个允许输入字段的来源/type/shape契约与候选语义schema；设计严格tensor/结构化语义投影，不将raw全stream、metadata或任意嵌套dict直接穿透。对每个禁止字段在顶层、各允许字段内嵌套和序列位置注入fixture，要求最终出口拒绝或已明确剔除；跟踪model入口实际可达性，而非仅扫描文件名。输出FIELD_LINEAGE.json和INJECTION_RESULTS.json；出口未实现则不得报leakage-free。
6. **S5 汇总（120s）**：覆盖矩阵逐要求链接真实receipt、fixture来源和未完成项。24/48与全8根未齐则SUITE_PARTIAL；即使48齐且无训练检查全过，也只报pilot_input_audit，不报Stage1科学Gate、Temporal Identifiability、H-reveal、compression或训练ready。

## 必要负例清单（均待执行，不计新物理/collection）

|编号|最小变更|必须检查/预期|
|---|---|---|
|T01|去掉一个state或action，26改25，NaN，requested/effective共享内存|原raw validator拒绝，各自原因明确|
|T02|action timestamp移一帧、start/end颠倒、非250Hz单间隔|原alignment validator拒绝，非仅manifest hash拒绝|
|T03|current换成state[1]、重复38DOF一份被改、RGB某component错hash|原current auditor拒绝，不另存“修正”current|
|T04|同一raw填两格、错root/current/candidate、pending假pass|pilot_matrix拒绝；仅登记结构负例|
|T05|严格prefix内改一个有效setpoint；free path不同prefix正例|原prefix verifier拒绝前者；后者不得错误失败|
|N01|F1母轨迹保持动作/真值不变、把任务换成另一对象|原对象选择/非目标保持verifier拒绝；单标签改名不算充分检查|
|N02|F2 on/inside/beside任务bundle替换、真实支持缺失|原目标关系/排他/支持门拒绝；等F2 root可用，资格结果不充当完整root|
|N03|F3少V/H、错轴、掉抓持、非法suffix顺序|原实现事件/连续抓持门拒绝；冻结shared-first-V不动，不做H/reorder训练数据|
|N04|F4相同终态但实际顺序对不上目标、缺A/B/C、非目标被动移动|原程序顺序/非干扰/终态门拒绝；仅有终态不能判成功|
|L01|path/branch/selected candidate/instance/planner phase|不能从任何模型输入字段泄露；合法三候选语义不是selected-ID|
|L02|未来RGB/物体pose/contact/verifier/success/finalstate/mask|审计分区可保存，模型出口禁止；不物化未来图像或H视图|
|L03|正常回答型instruction、oracle任务树节点、文件顺序|五字段结构出口不得携带；不训练分类器测猜标签|

## 已有CPU测试可复用但不能误标新套件完成

`tests/controlled_multi_future/test_pipeline_contracts.py`中PipelineContractsTest：test_primary_stream_26d_250hz_n_plus_one、test_raw_streams_reject_alias_and_placeholder_sources、test_runtime_trace_converts_to_n_actions_n_plus_one_states、test_model_view_rejects_path_and_branch_leakage、test_selected_arm_contact_and_f3_consistency、test_f4_non_target_and_slot_preservation。
逐个读依赖后以pinned CPU环境运行指定方法，禁用任何含真实GPU初始化的集合；现有historical测试通过不等于本轮真实24格全覆盖。
本目录test_inventory只证明输入盘点/作用域和浅层投影缺口复现，不将S1–S5标已执行。
