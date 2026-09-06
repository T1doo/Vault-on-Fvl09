# B三程序planner-only接口（CPU草案，未执行）

只有真正已发布的B Stage-A source evidence + Goal terminal + Guard terminal + source manifest四者文件hash/selfhash/scene/source/cleanup一致才可调用。2026-09-07已只读消费真实p48_f4_b_stage_a_001四份证据，source evidence receipt为8714090570cf6193aecc1df71ccb4ddb3aadced115945a1164025997de7134c7，135/1/0/0通过；三程序本身仍未运行。禁止构造fixture当实际资格。

纯CPU issuer是`goal_pilot48_v1.runtime.issue_f4_b_program.build_manifest`或`issue_from_reservation`；不reserve/写job/启动。固定450/3/0/0，child1800s/lease1980s，nonce base202609070400，三程序实际nonce为401/402/403末尾（完整202609070401/202609070402/202609070403）。主线程传真实reservation并发布。先验证并继承source Stage-A全部source/input hashes，补本新runtime/issuer/四份实证，不自动重新hash放行变过的parent source。

同物理场景current hash的CPU审计：capture_current的reconstruction是scene_seed/generator_version/source_commit与_simulation_configuration，不包含purpose、完整planned_scope_spec hash或Stage-A terminal字段。两种spec使用同B seed/layout、同hierarchical adapter marker、同validated_authorization_receipt source seal；直接调用真实_simulation_configuration于CPU fake scene，结果须与已保存Stage-A实际reconstruction配置逐字段相等。因此不预期出现纯purpose metadata导致的aggregate差异，真实RGB/state/current仍要在GPU场景捕获后严格比较，不能CPU宣称像素一定相同。

run(manifest)要求resource_caps恰450solver/3scene/0action/0collection、正整数planner_reset_nonce_base、B payload hash和Stage-B scene spec hash。四项前置字段均采用`source_stage_a_{evidence,goal_terminal,guard_terminal,manifest}_{path,file_sha256}`。每个program用base+ordinal(1..3)，slot ID `job_id-f4-abc-planner-source`等；对应physical_micro_slot_id不含末尾-planner-source。

使用原run_f4_program_planner_v2，不执行control，原42 API=12次10-goal grasp batch+30单goal=150真实问题，每个独立fresh scene。任一program/cleanup失败保留证据并停止剩余program，不进入physical资格。三份terminal envelope保留原spec/terminal/error/cleanup键，附加B scene与physical_micro_slot_id；成功时实际调用原下游isolation spec builder验证接口，但不发布或执行physical资格。

跨scene独立Goal meter日志按CHARGE累计对账；scene的trace reset不影响总体problem数。所有JSON走realization_utf8_io_v1 exclusive atomic UTF8。没有issuer/reservation/启动逻辑。主线程派生manifest时须继承已经校验的Stage-A全部source/input，并新增本目录所有源码和上述四个真实证据文件；此处source_inputs.json仅标识既有Stage-A source inventory，不冒称包括新增wrapper。

下一门：5个B isolation（A/B/C/AB/AC），总5scene/5action/720真实goal问题，其中common-X重新规划50goal不可因initialize_trace清零漏计。再后面仍有template/root/motion，三planner成功不等于physical成功。
