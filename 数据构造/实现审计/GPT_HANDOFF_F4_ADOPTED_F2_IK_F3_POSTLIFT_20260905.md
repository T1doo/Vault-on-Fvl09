# 本轮执行反馈：F4 已正式接收；F2 新 IK 失败；F3 post-lift 修订完成

依据完整读取的 [最新外审](https://chatgpt.com/s/t_6a9bba4a24f8819198b34df3697b5362) 执行。正文 15,338 字符原样保存在 EXTERNAL_REVIEW_F4_ADOPTION_F2_METADATA_F3_POSTLIFT_20260905.md；完整结构化决定见 EXTERNAL_EXECUTION_DECISION_F4_ADOPTION_F2_F3_20260905_V1.json。没有发现附件下载链接。

## 1. F4：批准的 CPU 采纳已完成，不再申请重复批准

原 root 已正式登记为 **1 development root / 3 r_pc trajectories，accepted via APPEND_ONLY_RECEIPT_RESOLUTION**。全项目 development accepted=6 roots/18 trajectories；没有新增物理运行或新采集轨迹。

正式文件位于：
`/nfs_share/lijunhui/Robotwin2/datasets/f4_root1_receipt_resolution_v1_1/`

- resolution.json
- branches/F4-ABC.resolved.json
- branches/F4-ACB.resolved.json
- branches/F4-BAC.resolved.json
- acceptance.json

Acceptance receipt SHA=`5416dc9e94cf8c534eb91e7b35fd9e9661c1f7bc142f96d6fcc6bf3f1b817723`；publication 文件 F4_ROOT1_ACCEPTED_VIA_RESOLUTION_PUBLICATION_V1.json，receipt=`4bca9893a4f476cf71b5745ad66c463b123f9eff1e762976f78e8d0e820ba21a`。

本次重新校验61个原依赖，包含三 branch/raw/manifest/sidecar/MP4/source traces、prefix/suffix artifacts、root/job/Guard和event log；按原loader验证artifact数组/hash，并从三条immutable raw重算逐步SHA和首分歧。P仍2851，raw/step hashes/root三路分歧均2926；2926不等于H_reveal或所有意图可辨识。

生产采纳入口是显式load_original_branch → validate_resolution → load_resolved_branch → audit_f4_root_with_resolution，不使用unittest.mock。finalizer保留原8个纯函数的科学/文件/计数逻辑，仅加入显式branch_loader；针对性source-equivalence测试验证函数文本除此之外不变。全部29项验收通过，原文件前后hash一致。9/9 CPU测试通过。

原job pass=false、child exit1、旧POST_CHILD失败均原样保留。重复执行只读审计返回already_registered=true/new_registrations=0；不重复入账。

开发中的两次失败也保留：第一次check-only将suffix loader三返回值按两项解包，未写派生文件；随后v1正式尝试因提取模块漏json import被root reader拒绝，保留resolution与三views，未发布acceptance。v1_1补import和真实disk-reader回归后才通过；旧partial namespace保留attempt_failure.json。两次均0GPU、原采集目录无修改。

未来collector的publication-order修改与本次采纳分开；active source未改。本轮未把独立CPU开发方案冒充已部署collector修复，也不因采纳成功授权下一F4 root。

## 2. F2：几何修正已实测生效，但第一中转姿态 IK_FAIL

专属执行代码、approval和CPU预检在commit c99f158发布后才上GPU。13/13 CPU tests通过：原9项加独立frozen table plane、live table bias、unknown post-counter和exact target hash检查。

实际运行：

| 项目 | 结果 |
| --- | --- |
| GPU | physical2 / GPU-4306d28e-0eeb-2e26-bda4-b1b44058f63e |
| 进程 | Guard1061757 / child-PGID1061881 |
| 时间 | 52.62秒 |
| scene | 1个fresh planner-only scene |
| queries | 1/6，第一段失败后停止 |
| physical / raw / root | 全部0 |
| inside | 原Run3 5/5保留，文件SHA不变 |
| cleanup | scene、cache、lease、process group、GPU baseline全部通过 |

目标绑定不再报错：live actor-origin补偿、geometry-centre XY、sealed qpos/EEF/actor恢复、table0.74+table_z_bias与冻结layout全部通过。实际targets SHA保持`39e04cb57afeb64236a6f549e37a1dc1b9f9f09a3861908ce9eb7173e2ae51ae`。

第一段：
`beside_asset_bound_carry_hub`

其冻结EEF pose为：
`[-0.09937910691974647, 0.054842759211695825, 1.0498586893081665, 0.5017174026769478, -0.498810972458648, 0.5011190506874883, 0.4983442170267715]`

真实side-channel：

- status=MotionGenStatus.IK_FAIL
- valid_query=true
- success=false
- used_graph=false
- position_error/rotation_error=null
- solver attempts=10（同一plan_single内部尝试，不是10次外部query或额外重试）
- solve_time=0.0566613674秒；total_time=0.0863754749秒

因此当前证据是“选定中转EEF目标没有被当前IK求解器解出”，不是坐标错误，也不是已证明physical infeasibility或确定发生碰撞。不能把它写成11/11 route qualification。scene counter before0/after1/delta1，accounting_complete=true，error=null；科学失败正确传播exit1，POST_CHILD validation_pass=true/job_succeeded=false。

GPU2 postcheck=14MiB/0%/P8/no compute，task-owned PID均不存在；GPU0当时有其他用户任务，未干预。

证据：F2_BESIDE_ONLY_TERMINAL_PUBLICATION_20260905_V1.json，receipt=`8288e1c064bfb51e94ff30bae2b4e38f2207baf3f43a47e5a9187dde23b69e7f`。

**需要的下一意见**：针对这一确切carry-hub pose做最小路线/中转姿态impact review，明确后续有限planner-only诊断方案。当前单次授权已消费，不能自行换hub/seed重试、重跑inside/full11或启动root。已解决的metadata/source/table/receipt问题无需重做。

## 3. F3：只修post-lift判定，完成所要求的CPU修订

新目录：`f3_preclose_candidate_micro_runtime_v1_1/`。

新函数：`post_lift_audit.py::audit_micro_lift_trace`；candidate_executor保存lift execution receipt，并在25mm动作后保持夹持记录50帧，再调用该函数。

冻结诊断合同：

- hold250后的瓶位作为baseline；lift末端及全部confirmation实际rise至少20mm。
- lift+confirmation全窗口持续有效selected-gripper contact。
- 50帧confirmation全部无bottle-table/pad物理接触。
- relative grasp transform全窗口最大drift≤5mm/0.05rad，而非只看两个端点。
- 按原physical classifier拒绝执行臂自碰、arm-support和非预期arm-bottle contact。
- 保存检查lift receipt的段ID、start/end、planner status及原30mm/20mrad EEF tracking界限。
- 验证frame数量、step连续、timestamp严格递增、pose有限性及contact字段/shape证据；缺失不判成功。

这是新微门合同，不重判旧四条失败轨迹。未给20mm/50帧加事后调参自由。

测试：12/12直接post-lift测试 + 原23/23 regression，总35/35；覆盖仅最后一帧离桌、无实际rise、中途滑移后恢复、缺帧/重复step、自碰/支撑碰撞、不完整contact、缺字段/receipt、lift失去接触及有效case。

Guard、job_runner、原test_executor与上一版**byte-identical**；Gate V1.1、四候选/order、seeds、qualification顺序和52queries/12scenes/4attempts/两次pass停止均不变。新增manifest binding仅涉及post_lift source与contract；没有重写通用审批或Guard。

真实CPU Guard→runner→四Stage-A bound-spec preflight通过，output/Guard/cache-job仍absent，0GPU/scene/physical。proposal仍approved/GPU=false。

窄复审入口：

- PROPOSED_F3_POST_LIFT_MICRO_MANIFEST_V1_1_20260905.json，manifest SHA=`37d9a4ea7009c04ff73fb6f8f7b470e082ec8f0833bb7afc2d5ffb409f494f8a`
- F3_POST_LIFT_CPU_REVIEW_20260905_V1_1.json，receipt=`e764485818de8cfe48010dd860e070bec02f5e3cf2f630529becbdbadbd2cb72`
- 新post_lift_audit.py、test_post_lift.py和candidate_executor.py（其余与旧版一致）

请仅复审post-lift audit、接线、针对性测试和新source/proposal绑定。通过后再给精确micro执行决定；目前不自行启动F3。pre-close/post-lift Gate仍是检测与阻断措施，不是碰撞模型已被修好或新四候选可抓住的证明。

## 4. 当前统一进度

| 家族 | 已验收development | 当前状态 |
| --- | --- | --- |
| F1 | 5 roots / 15 r_pc | 等真实invariance设计与独立批准 |
| F2 | 0 roots | inside5/5保留；beside first hub IK_FAIL，待最小route review |
| F3 | 0 roots | post-lift CPU修订完成，待窄复审 |
| F4 | 1 root / 3 r_pc | accepted via append-only receipt resolution；不重跑 |

统一readiness为STAGE1_READINESS_F4_ADOPTED_F2_BESIDE_IK_F3_POSTLIFT_20260905.json，receipt=`12279e4a882358e1da5fd5482ed6d75ae81570ef81ceaed5e323eb18c4082638`。

Development accepted=6roots/18trajectories。Stage1 authorized accepted=0/48，formal=0/360，Stage0不重开。训练、H-reveal、compression、π0.5未授权。当前无本任务GPU残留；下一步只有F2新route review和F3窄复审，不再请求F4采纳许可。
