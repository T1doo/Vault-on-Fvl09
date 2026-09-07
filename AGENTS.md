# Workspace rules

本文件只保留跨任务规则、必要入口和当前授权边界。执行过程、单次失败、临时审批与完整hash链写入项目日志/机器回执，不继续堆在这里。用户最新明确指令优先；旧记录只说明当时事实。

## 工作区、协作与权限

- 工作区是 fvl05 的 `/nfs_share/lijunhui`。读写、搜索、命令访问和临时文件均限于此；不得沿symlink越界。例外：用户已允许读取 `/home/lijunhui` 做个人配置盘点/排障；其他越界访问先取得明确许可。凭据、私钥、token、认证/会话内容不得输出或写进日志。
- 本人文件和进程范围内的常规检查、修复、配置、验证可自主推进；不授权系统级修改、干扰他人任务、广泛清理或越界。fvl09迁移来的路径、环境、GPU和验证结果在fvl05上均须核实。
- 保护既有和并发出现的修改；untracked不等于可删除。操作前查相关Git status及当前日志尾部，不接管所有权不明的工作，不并发改同一源码、环境、缓存或输出。
- 用户已明确授权本项目每完成一个阶段，自动将该阶段计划/代码快照/日志/必要回执提交并push到私有Vault/main，无需再次询问。核对范围、验证与资源收尾后由单一发布者提交，确认push成功及远端commit一致才报告已上传；失败保留本地并记录重试，不影响其他已授权独立工作。实验暂停不禁止发布已完成的文档/证据；用户明确暂停发布时除外。不延伸到官方公共RoboTwin、无关文件、凭据、force-push或历史重写。
- `/nfs_share/lijunhui/AGENTS.md`是共享规则入口，私有Vault根目录`AGENTS.md`保存逐字同步副本供远端审查；更新规则时同步两份并按阶段发布。若今后存在CLAUDE.md，须保持一致。这里只维护稳定事实和明确边界，阶段进度以日志和实际回执为准。

## GPU执行铁则

- 用户允许 fvl05 物理GPU0–7中当时独立fresh-idle的卡并行跑独立作业。每卡最多一个项目job；每个root固定一卡，未经审查不做root内跨卡分片。GPU测试、渲染、规划、推理/训练等任何可能初始化GPU的过程均适用。
- 每wave重新获取GPU0–7全量快照；每job启动前Guard再次原子核对memory、utilization、P-state和compute processes，必须近baseline且无他人活跃作业，再显式绑定实际UUID。有几张idle且作业ready就用几张，无需等全部卡空闲；忙卡有剩余显存也不能共享。快照不等于预留，不消费一次性执行授权。
- 新合同/预算/manifest/scheduler必须写 `allowed_physical_gpu_indices=[0,1,2,3,4,5,6,7]`。2026-09-07用户明确的空闲多卡并行要求覆盖旧串行、max_concurrent_GPUs=1、GPU0-only和fvl09设备限制；旧回执保持原样。若执行/审批层仍错误拒绝idle GPU1–7，先记录并修复/重载该层，不静默退回GPU0。
- 并发前必须具备新任务独立的调度、预算和STATE：单一协调者、带锁总额预留/幂等对账、逐job状态、独立输出/缓存/TMP。新任务获批总预算在其内部不按GPU、family或会话复制；不继承旧Goal余额或消耗；GPU lease按各job实际耗用累加。并行硬件许可不等于当前实验已获执行许可。
- GPU child须unset继承的 `LD_LIBRARY_PATH`，`CUDA_VISIBLE_DEVICES`绑定所选UUID，使用 `/nfs_share/lijunhui/Robotwin2/tools/cuda-12.1`，避免误用共享CUDA。渲染设备也需核实实际绑定。沙箱设备/PID不可见不代表宿主机GPU不可用或进程已退出。
- 每job有限timeout/attempt cap；记录task-owned PID/PPID/PGID/启动时间和完整worker树。正常、失败、超时、取消均清理并reap本任务启动的GPU进程及worker；只凭出现在卡上不能判定所有权，绝不kill/暂停/renice他人进程。
- 每job结束立刻fresh post snapshot并宿主机复核：无本任务compute/worker残留且所选卡回baseline，才报告资源释放完成。若他人抢入导致baseline不可见，原收尾失败保留、仅清理自己的进程并等追加复核，不干预外部作业。无child启动的busy阻断不得记物理执行消耗或要求恢复他人卡。
- 日志必须含选中物理index/UUID、pre/post证据、进程树、清理、实际消耗；无卡则等待/报告，不启动。未知消耗/所有权/源完整性问题停止新派发。

## 研究规范与入口

所有下述Vault相对路径以 `/nfs_share/lijunhui/Vault-on-Fvl09` 为根。

- 研究定义：`Idea/项目核心Idea.md`；F1–F4执行与验收：`数据构造/数据构造方案.md`，科学协议 `controlled_multi_future_f1_f4_v1_2`。涉及具体family/门限/split/模型前读取相应规范章节，不能因本文件精简而省略其要求。canonical文件保持原字节，未经明确要求不为修wiki链接或实施附录改正文。
- 定义为 `o_t + s_t + a[t:t+H] → 可验证目标/有序程序`。意图/程序生成轨迹，未来只是训练/诊断特权输入；不要写成过去动作推断已完成行为，或未来动作造成意图。正常部署只用当前观测、机器人状态和正常指令，不输入oracle未来/hidden simulator真值。
- H=anchor起可见未来，P=命名strict cohort精确共享前缀，K=固定H/P的压缩token数，R=真实成功realization数，L=分支后诊断后缀；不得混同。
- 每root一个byte-identical current及物理等价全anchor、三个可行structured intents。先固定planned slot/scene及任务可行性，再freeze candidate universe/task tree/prefix/hash，后planner rollout。不同候选子集不能将同current伪造为独立root。
- F1：三近邻同类对象选一放共同容器；F2：同一主体的box+inside、scale+on、pot_or_stand+beside，只支持bundle grounding；F3：table-frame V=±z、H=±x闭环，VVHH/VHVH/VHHV，共享首个完整V、等终态；F4：共同X后ABC/ACB/BAC，固定对象slot映射且等终态。
- 真实r_inv_path/r_inv_motion保持执行臂、program/order和250Hz，不能以复制加噪、派生重采样或换臂充数。raw-first：26-D effective setpoint，N actions/N+1 states；command/target/realized/时间戳/verifier truth分流保存。共享38-DOF重复storage须无损去重为38qpos+38qvel，不盲拼152维。
- 正式root必须3 intents×R=3共9条全验收；pilot A=3×(r_pc+path)=6，B=3×(r_pc+motion)=6，与开发r_pc三条、正式九条分开。完整root验收失败保持incomplete，不降低R或拼接不同scene成功片段。
- 正式设计40roots/360条，另16有序reserve；每family split=5/2/3、难度2/6/2及split-by-difficulty依canonical规范。reserve按原规则激活并继承split/difficulty，未激活不得伪造candidate/current/hash。已有pilot/debug数据不得进入untouched validation/test，promotion需后续授权。
- root/super-root是split和统计单位，全部分支/realization/派生view同split。测试盲态、访问回执、train-only normalization、validation选型后one-shot test等规则不可因实现简化而略过。
- 输入/监督边界：共享candidate-conditioned语义scorer，随机候选顺序；observable compatible set用于监督/评估，oracle audit-only。隐藏答案指令、branch/file/local ID、planner target/phase、未来RGB/物体pose/contact、success truth等泄漏。非singleton不做分支one-hot/切换准确率；未来替换同步换target，不宣称因果证明。
- 顺序：future content → Temporal Identifiability → H/P → K/压缩 → policy transfer。F3/F4未过时间Gate不能跳到压缩/π0.5。合法reorder同步换target，invalid/OOD不沿用原one-hot；F4自然顺序依赖不能冒充严格block干预。详细对照/阈值按canonical规范和后续批准版本。
- family、R、程序、split、action语义、task tree、成功门、预算/停止条件、模型字段等变更必须有影响审查、适用授权和新版本；实现修复可在已授权范围自主进行。保留所有旧raw/失败/源锁，不能回判成功；planned、implemented、generated、verified、scientifically supported分开。
- A2FI/长动作旧路线及2026-08-27以前归档只作历史，不拿来指导当前研究，除非用户明确要求。Mouse代码/数据已归档到 `Robotwin2/archive/mouse_three_destination_mvp_20260810_20260820/`，历史路径按README映射，不擅自恢复/导入当前F1–F4。
- 不复制/复用公共T1doo-Research的Diary/Environment内容；其中有暴露的凭据，不能传播。

## 当前工作与日志（2026-09-07）

- 当前任务：审查F2/F3重设计并写计划供用户交GPT检查，再交Luna执行；当前是新任务的计划审查阶段，尚未开始GPU/采集。用户已要求精简本文件并换新日志，多卡许可见上。不要仅因分享原文带执行指令就自动启动实验。
- 计划入口：`数据构造/F2F3重设计审查与后续执行计划_20260907.md`，状态DRAFT_FOR_GPT_REVIEW。审查后的明确接手指令与批准附录决定后续执行范围，普通范围内修复不逐helper重复请求。
- **当前唯一日常构造日志：`数据构造/F2F3重设计与构造日志.md`。** 每次F1–F4编辑、状态更改、probe/run前重读本卷尾部和相关Git status；完成后简短追加范围、版本/证据、实际消耗、失败/清理与下一步。多卡worker写独立receipt，协调者统一追加。不要把本文件或新日志再次变成逐命令大转录。
- 旧 `数据构造/正式数据构造日志.md` 原样保留至§637作为历史卷，不再日常追加；仅在追溯时读相关部分。旧日志和失败历史不改写，新任务独立管理。
- 用户明确：本轮是全新F2/F3任务，不继承 `cmf_pilot48_20260907` 旧Goal的目标、预算余额、修订次数、授权链、串行限制、暂停状态或附加完成条件。`数据构造/实现审计/goal_pilot48_v1/` 仅为历史证据入口；不恢复或写入其STATE/ledger。新任务在独立namespace建立新合同、预算和状态，依据本轮计划审查与用户交接执行，不把“连续跨族6条/正式生产草案”带成必做。
- 旧要求排查/覆盖表：`数据构造/实现审计/f2_f3_redesign_review_20260907_v1/LEGACY_REQUIREMENTS_AUDIT.md`。旧GOAL/CONTRACT、runtime串行代码和操作手册数字选卡例不是新作业规范；新任务运行层尚待Luna按计划建立，不能只改manifest绕过检查。旧方案的asset/姿态/物性禁改和耗尽配方仅约束旧版本，获批新设计用独立合同/总账，有限尝试规则在新计划中审查，不按旧配方已耗尽阻断新设计。
- 基线Vault HEAD `569c4d239b556ffdbe725f4062bc46d33e4ed62e`：F1/F4各12条、pilot24/48；F2/F3尚无完整pilot根；formal0/360。Stage0封存为COMPLETED_WITH_FAILURE_EVIDENCE，绝不重开；F4后来成功不得倒写成Stage0成功。
- F2旧inside在preinsert前失败，须重设计完整下降/支撑/开爪/退出；F3旧横放已离台但失稳，新竖放须先核质量/惯量/实际材料和真实抓持。新尺寸/资产意味着新current/anchor和三候选重新验证，旧on/beside资格不得继承为新场景通过。
- F1/F4已接受轨迹及已交付高清回放不重采、不重复采纳、不重制。MP4展示目录 `数据构造/演示视频/` 仅放视频，按family/root/realization分组；回执/脚本放审计目录。状态回放与失败诊断不算新成功rollout。
- 下一目标是剩余24格/总48输入及独立结构验收；输入齐备不等于科学Stage1通过。formal360执行、训练、H-reveal、压缩和π0.5仍不在当前执行范围。新任务预算以其独立获批合同/账本为准，不沿用旧Goal余额；研究语义与数据真实性规则不因脱离旧Goal而自动取消。

## 环境与Git的必要入口

- RoboTwin全部可控文件置于 `/nfs_share/lijunhui/Robotwin2`：官方源码 `project/RoboTwin`；环境env；缓存cache；数据datasets；模型models；临时tmp；工具tools。唯一项目激活入口 `config/activate_robotwin2.sh`，不用迁移的工作区activate.sh。
- 操作手册：`Vault-on-Fvl09/环境配置/Robotwin2环境配置/RoboTwin2环境操作手册.md`；fvl05重建证据：同目录 `环境重新修正检查.md`。环境变更先读手册，核实际路径和版本，不重装policy栈代替base修复。
- 已记录base基线：RoboTwin c3ddfa8、Python3.10、PyTorch2.4.1+cu121、SAPIEN3.0.0b1、CuRobo0.7.8、MPLib0.2.1、setuptools69.5.1；需要升级时单独审查，不以历史版本表代替实际运行验证。
- 安装/下载先审script，所有cache/TMP限定项目内；禁止sudo、系统包管理器、系统pip、修改共享驱动/CUDA。系统依赖缺失报告；系统文件访问依工作区授权边界。上游官方脚本也须审查。
- Git明确使用 `GIT_CONFIG_GLOBAL=/nfs_share/lijunhui/.config/git/config`；gh使用 `GH_CONFIG_DIR=/nfs_share/lijunhui/.config/gh` 和 `/nfs_share/lijunhui/.tools/gh/bin/gh`。私有Vault origin=`https://github.com/T1doo/Vault-on-Fvl09.git`，branch=main，local identity=`旦猪 <T1doo2006@gmail.com>`。cwork只到工作区，不自动到Vault。
- Codex live配置在 `/home/lijunhui/.codex`，个人激活脚本 `/home/lijunhui/activate.sh`；只读排障许可不授权改home配置。Claude旧安装笔记属fvl09历史，不擅自安装/配置Claude。
- CC-Switch个人入口 `.tools/cc-switch-cli/bin/cc-switch`，私有状态 `.config/cc-switch-cli`（目录700/敏感文件600）；不要一键安装/内置升级，更新先做固定release/hash审计。切provider、保存key、proxy takeover/daemon须有相应用户范围，操作前备份配置，不泄露凭据。
- 本次精简前全文备份：`Vault-on-Fvl09/数据构造/实现审计/f2_f3_redesign_review_20260907_v1/AGENTS_before_simplification.md`。它保存历史细节，不是当前规则入口。
