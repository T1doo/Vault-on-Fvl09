# F4-B source Stage-A Goal runtime V2

CPU实现；无GPU/新scene/qualification回执/签发。执行入口 `goal_pilot48_v1.f4_b_runtime_v2.runtime.run(manifest)`，测试模块 `goal_pilot48_v1.f4_b_runtime_v2.test_cpu`。

CPU issuer为 `goal_pilot48_v1.runtime.issue_f4_b_stage_a.build_manifest(job_id,reservation)`（别名组合入口`issue_from_reservation`）。它绝不reserve、写job或启动GPU；主线程独占reservation与exclusive publication。固定job命名`p48_f4_b_stage_a_*`，child1800s、lease1980s。任何已存在job/output/guard/meter/cache namespace均拒绝。issuer preflight模块为`goal_pilot48_v1.f4_b_runtime_v2.test_issuer`，包含runtime全部测试。该测试的generic dispatcher转发只mock authority loader（因为不得创建真实reservation），其CPU分支和测试加载是真实调用，Meter.install被禁止。

issuer先验证原F4 parent文件精确hash `c178bc3397226a1cb64a968acfae55ee8f86f55da24cd91813ae4496cfb982df`、manifest self-hash及其全部绑定path/file hashes与F4 asset hashes，再继承；旧A receipts保留为lineage而非新B资格。补充完整active controlled/envs Python源、CuRobo C++/CUDA/YAML、全部task_config、Aloha URDF/meshes/YAML、tray0的metadata/visual/collision/points_info、新B proposal/V1/V2、generic runtime/UTF8 helper。procedural blocks和table/pad的创建由源树绑定。不会将变过的parent dependency重新hash为新合法值。

## 必须由主线程绑定的job字段

- `runtime_module`上述模块；`runtime_file`为本目录runtime.py。
- `test_module`上述测试；`resource_caps={solver_problems:156,fresh_scenes:1,action_scenes:0,collection_attempts:0}`，不允许改值。
- `b_payload_sha256=payload()['receipt_sha256']`，`planned_scene_spec_sha256=runtime_spec()['planned_scope_spec_sha256']`。
- `output_namespace`必须为新的workspace目录，不能复用失败输出。
- Guard/UUID/lease/pre-post/cleanup由generic Goal runner包围；底层meter须在import/runtime前安装，dummy warmup跳过单列，不能把它算作已执行0次规划。

## 真实N预算复核

原`build_f4_stage_a_targets_v1`对A/B/C每role调用一次原F1-derived grasp chooser，4个contact points各一次10-goal batch，共12 batch=120个独立目标问题；再每role5个targets(pregrasp/grasp/lift_mid/lift/neutral)，15个单goal链式规划。正常完整上界135，原API计数27。保留原`job_budget_v1`的48 API limiter，但新wrapper同时限定12 batch/15 chain/每batch N=10；156为Goal预约余量，不允许扩展目标或额外批次。

`query_rows.json`按原scene实际receipt的batch N重算。wrapper读取同作业`<output>_meter/events.jsonl`独立CHARGE日志，验证逐资源amount/total连续，再核对solver实际N、1scene、0action、0collection；记录日志当前字节hash（generic runner稍后追加METER_CLOSED，此处明确是运行时前缀快照）。不一致就accounting_complete=false且不得发布passing source证据。generic Goal底层meter是独立测量，wrapper计数不能替代它。

## 写入与结果语义

原HighLevelPlannerRunner只在私有globals副本中替换exact-B spec validator及writer。旧两次`receipt.json`写入分别改为`stage_a/started.json`与`stage_a/terminal.json`，使用现有realization_utf8_io_v1.write_new，显式UTF8、exclusive、atomic，不覆盖已有字节。其他本地JSON同样使用该writer。

输出`pass`表示基础设施/cleanup/可核算完成，不表示source资格通过。`scientific_route_pass`与`qualification_pass`为真正资格结果。`scene_attempts`、`accounting_complete`供generic dispatcher使用。完整计数的普通planner失败、无合法抓取目标或visibility失败可清理封存为scientific false，不能推动下游。缺counter/错误seed/worker路径/任意其他异常仍是基础设施失败。

成功source证据从原15段实际`planner_status`、渲染visibility、共同neutral目标、真实seed、scene ID、cleanup及135问题拓扑推导；不继承A成功。生成`source_stage_a_evidence.json`后，下一且仅下一门为三份精确B候选/program/nonce/source_scene绑定的ABC/ACB/BAC planner-only terminals（3scene，450真实goal）；之后仍需5isolation→3template→root→motion，不能直接跳到collection。

## 所有依赖/锁定输入

`source_inputs()`返回当前准确文件hash和整个active controlled Python tree hash；显式文件含本V2所有.py、V1所有.py、原B proposal及realization_utf8_io_v1。B proposal receipt固定39c1f6238014b0959f43d4d4748391dd79b7c1528703c5609f0039a428984e0f；source seed2026090604，原common-X/tray、grasp policy和Gate不改。

active controlled tree固定3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7，涵盖原high_level_planner_runner_v1、family_runners_v3_1/v3_3、high_level_runtime_specs_v1、planner_qualification_manifests_v2_3、f4_hierarchical_template_search_v1、f4_stage_b_geometry_contract_v2、所有adapter/scene/runtime trace/canonical hashes等传递依赖。

主线程Goal manifest仍必须绑定active tree之外的Robot/Scene环境代码、Aloha URDF/YAML/collision spheres、tray模型/碰撞/metadata、原固定CuRobo库和环境、Guard/meter source。此wrapper不新增asset，不改初始化策略；不能把本目录小范围hash清单冒称整个runtime环境已封存。

CPU测试只用临时目录和fake scene/planner驱动原runner生命周期；测试fixture不会进入持久科学证据或当作GPU结果。未运行GPU测试。
