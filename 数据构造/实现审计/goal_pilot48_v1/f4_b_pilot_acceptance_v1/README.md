# B六格独立接受候选审计（运行中不执行最终审计）

audit.build_candidates(output)为纯builder，不写STATE/pilot_cells/预算，不GPU。主线程通知producer已终结后才能执行真实全量审计。缺Goal/Guard/cohort/index或任一final receipt返回pending；绝不把receipt.provisional.json当final，CPU测试只用临时负例。

终端要求：真实Goal pass/accounting/current完整六项/科学结果、Guard UUID/physical index/cleanup/baseline/lease、独立meter closed及0/3/3/3与3program factory身份一致。随后递归验证root001旧失败+资源acceptance/budget链，调用现有V2 current_recovery，不改原Goal。

三motion逐一重算raw完整性、N26@250Hz/N+1、raw/trace row0、旧38+38无损current/三路RGB、原family verifier和角色顺序、MP4。原V1.3 variations_from_trace用实际旧/new trace planner-ID窗口重算3段retime采样数/执行时长比例，并与保存variation receipt完全相等。全三finalized branches和Goal/cohort/index逐字段一致，原finalize_three_branch_root再次运行且不得再改变branch；六pc+motion finalstate重新比较，六raw hash/动作数组hash各唯一，防复制填格。

报告cells采用pilot_cells的family/pilot/program_id/realization/status/evidence结构，含raw/trace/video/semantics/current/anchor/cleanup/失败来源。status=verified_candidate_pending_main_registration、pilot_input_accepted=false，仅供main显式按六个精确key登记，不自动把18改24。记录登记前pilot_cells文件hash；已有不同证据不覆盖。同一shared current来自本次后续B motion，明确root原先未保存RGB，绝不用A current/MP4伪恢复。

限制：原family verifier记录与root级原finalizer重新核验，未重跑SAPIEN或每个物理validator；当前源在producer运行期间只准备并执行CPU负例，没有执行真实最终接受审计。若成功，main可独占将报告写入新不可覆盖namespace后再决定登记。
