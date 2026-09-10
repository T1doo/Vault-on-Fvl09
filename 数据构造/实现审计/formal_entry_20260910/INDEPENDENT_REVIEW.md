# 第二轮独立定向检查（CPU运行层冻结）

状态：`CPU_RUNTIME_READY / FIRST_WAVE_PHYSICS_PENDING`。本轮实际四族调用接口、磁盘验收、恢复与副本流程通过以下CPU边界测试。此状态不授权GPU，不证明新场景物理可行或科学Stage1通过；预算/调度附录的用户集中确认仍是执行前边界。

独立检查者仅编辑本文件及 `test_independent.py`，未修改实现源码、旧数据或预算，未执行 GPU、planner、物理场景、训练或渲染。未将实现者的测试通过当作独立检查前提。Portable 的小型合成输入构造器复用实现者 fixture，校验调用、篡改动作和断言由本检查另写；fixture 不是实际机器人证据。

## 已复现并修正的问题

| 具体问题 | 独立检查及修正结果 |
|---|---|
| 计划可重复 primary rank、改变近重复阈值和 reserve policy | 原版本实际接受反例；现在显式冻结 rank/ID/阈值/policy，反例拒绝。 |
| 物理签名随 `material_source` 注释改变 | 现在签名只取明确物理字段；改 root ID/seed/注释不改变签名。 |
| reserve 可由任意部分失败集合或 remaining 波先消耗 rank1 | 固定完整 wave barrier；逆序完成得到相同映射，重启不重复分配；首波未结束不能进 remaining。 |
| 副本 candidate/target 只互相比对，未绑定原 receipt | 改 manifest candidate 与同步改 supervision、重算其文件 hash 后仍被拒绝。 |
| 副本 root finalizer 可替换后自行更新 manifest hash | 现从已复制 source index 核对预期 root finalizer hash，拒绝该替换。 |
| 九格根可由任意九个 key 构成 | 当前检查真正三 program × 三 realization、同 root/spec/current；重复同一 cell 拒绝。 |
| 重试已发布 root 未重新核对内部文件 | 已发布九格 fixture 的内部 trace 被破坏后，幂等发布重试拒绝。 |
| Prefix 限制误扩至全部 r_inv | Portable root prefix 限制已仅应用 `r_pc` 三格。 |
| F2/F3 显式 spec 改 pose 但旧 self-hash 仍接受 | 当前预检拒绝 stale hash；缺原资产绑定、缺 native source 绑定也拒绝。 |
| F2 primitive size 可改变但 verifier 仍使用旧半尺寸 | 变更 box/scale/stand size 并重新自哈希也拒绝，避免场景与验收几何分歧。 |
| F1 恢复读取错误 suffix artifact 路径 | 独立指出 `suffix_preflight/.../frozen_suffix_artifact` 与实际 `suffix_artifacts/program` 不一致，已修正。 |
| F1 早期失败尚无 prefix，但恢复仍强读旧 prefix | 只在原 prefix 存在时绑定复用；已有 prefix 使用实际数组/current/anchor核对并保留旧不可变artifact。 |
| F4 qualification 异常遗漏 query 与时序原件 | 已改为 finally 记录每 scene 起止、query、exception、cleanup，异常前 partial trace保留。 |

## 已执行的独立检查

`test_independent.py` 最终22个用例：合法40主/16 reserve、F2设施3/3/4位置分配，NaN/Inf/负尺寸/未知参数/重复realization，配置不共享可变对象，rank与policy冻结，物理签名，reserve反序/重启/缺barrier，包候选和finalizer篡改、缺相机/anchor/重复role、源变动、九格重复、真实3×3 fixture与已发布包损坏恢复，以及F2/F3源/资产/geometry预检、统一execution_cli的F1正例完整调用和自动副本发布。

Native preflight 独立进程确认拒绝发生在 `native_scenes`、SAPIEN、Torch 导入之前。此项只证明拒绝路径正确，不证明实际GPU场景初始化正确。

## 四族实际副本：独立禁止源目录读取

分别加载每个包内自己的 `reader.py`，在模型读取前安装 Python audit hook，拒绝打开原 datasets、active RoboTwin 和 Vault 路径；读取成功。原路径仅用于audit说明。没有重新复制这些样本。

| Family | manifest SHA256 | reader SHA256 | state / future | RGB |
|---|---|---|---|---|
| F1 | `099ca5e24236227bf6c90462b7dbaf43903a51944da812246cd77b71a6ee56df` | `bb844f7502e7045a742078f82f6579efbbd670905d448692f15ba3059d7cdbb9` | 76 / 4203×26 | 3路 |
| F2 | `60cf1c3a66a07d649b4b10eea57d204b82f7e854859b4992b519a2eea0b3c636` | `9175a33d49e8762aecd0cc1eb8f5af4074ccef9ee14d33b4ea4c6234cfaa69b8` | 76 / 4189×26 | 4路 |
| F3 | `cac9ae70c29b4adb4192ec8e952a321848b33bf1d0c2f4298f1196ed79298a0d` | `9175a33d49e8762aecd0cc1eb8f5af4074ccef9ee14d33b4ea4c6234cfaa69b8` | 76 / 5508×26 | 4路 |
| F4 | `5b008e777e9f4a25c4ea727d77bf647f93b8428436ce2454ce339881b36c1382` | `9175a33d49e8762aecd0cc1eb8f5af4074ccef9ee14d33b4ea4c6234cfaa69b8` | 76 / 12018×26 | 3路 |

包目录：`/nfs_share/lijunhui/CVPR_FutureIntent_Data/formal_entry_20260910_samples/{F1,F2,F3,F4}-final`。四包均3候选，`target` 不在 `inputs`；属于原有轨迹的有限迁移适配，不能视为新九条正式根已真实采集。

## 实际调用链与预算注意

F1/F4 每个三格 cohort 的源码调用为 pristine1、task-feasibility3、独立prefix1、suffix-preflight3、collection3，共11 fresh。三个cohort组成九格时基数33 fresh、至少21 action、9 collection；恢复、额外资格另计。不能继续写“九条第一格自带prefix，除此只需三个资格scene”。

F4另有3个真实planner资格scene、5个物理isolation scene。源planner每程序上限12 target construction +30 chain=42 queries。`native_f4_qualification.py`已存在独立新布局资格生产入口；本轮只阅读/CPU检查，未执行。新场景可达性、接触、camera native API readback、实际耗时及所有完整九格物理通过仍待新授权实测。


## 最终冻结、复跑与覆盖边界

源锁：693个运行文件（新运行层 + active controlled_multi_future + envs），`source_bundle_sha256=dfbb2fd48a195d147939bcfd4e1790ecf1db5cd917249cc7df67a239a18c04fb`。

本独立进程在最后冻结后重新运行所有定向套件，合计79个通过：独立反例22，launcher9，F2/F3生命周期2，F4生命周期2，F2/F3参数绑定3，scene8，portable8，formal exporter3，F1入口12，F4资格/工厂10。这里的79是测试数，不是成功轨迹数。

| 实际覆盖 | 方法与限制 |
|---|---|
| F1统一CLI→dispatch→九格→独立终态/输入→自动seal/copy→九包读取 | 仅替换 native_adapter 为明确synthetic backend，runner/finalizer/export/copy实际执行；synthetic结果research_eligible=false。 |
| F1原始orchestrator逐格恢复 | 第一轮red通过、green失败立即停止；恢复只执行green/blue，red原始raw字节不变。 |
| F2/F3 native root状态→磁盘独立验收→source seal→copy | 替换整个物理cell engine边界生成明确synthetic磁盘数组；没有覆盖native_cells内部planner/SAPIEN行为，不能据此宣称其物理已经通过。 |
| F4原始orchestrator九格及恢复→独立事件/终态→seal/copy | 仅替换模拟器adapter；包括失败后只恢复缺格、九包禁源目录读取；没有执行新布局资格物理任务。 |
| 资格入口 | 新F4布局重算/source与slot绑定、3 planner+5 isolation生产调用已接线；CPU检查绑定构造，不执行资格场景。 |
| 首波launcher | Guard、共享ledger调用使用显式fake host backend；真实两进程NFS锁测试；授权false在GPU snapshot前拒绝。未运行HostBackend GPU child。 |

最终集成检查另发现并修正了一个会误报完成的接线：不能把child退出码0等同于成功。最终execution_cli对失败返回非零并保存execution_result；launcher重新读取独立root接受证据、九格身份、副本root与registry及全部九个包，零退出但缺证据明确FAILED。自身GPU PID未退出会保留未解决的资源归属状态；GPU lease计量改为acquire到release，子进程用时另存。

一条中间测试命令未设置live RoboTwin PYTHONPATH，出现ModuleNotFoundError；按原模块调用要求设置PYTHONPATH后3项绑定测试通过。未以该环境导入错误修改实现，未隐去其原因。

最终复跑命令统一使用`PYTHONDONTWRITEBYTECODE=1`及项目env Python；涉及native CPU helper的套件加`PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin`，独立预检和F1/F4套件在分离进程运行，避免其他测试的模块导入污染“拒绝发生在native导入前”的检查。

本轮源文件界面与边界测试中未留有已复现但未修正的阻断项。原始robotics控制在新布局上的可行性、native相机API/挂载实际readback、接触稳定、真实prefix与全终态、Guard宿主机行为、真实资源消耗，仍由后续获批首波负责验证。CPU通过不允许跳过这些验真条件。


## 首波预算及最终fail-stop复核

最后仅launcher停止状态有一项局部补丁：`FAILED`及`SOURCE_CHANGED`与`UNRESOLVED/BUDGET_OVERRUN`一同禁止重新派发。补丁后重新执行launcher8项通过，其中零退出缺独立接受的测试还验证第二次调用在snapshot前停止。其余源未变，该补丁后继续加入下述scene鲁棒性修复，最终源锁以最终交付复核的dfbb2fd4…为准。

已对照`CALL_CHAIN_BUDGET.json`与首波manifest逐job相加：两根F1基数66 fresh/42 action/18 collection/384 solver；允许各cohort有限恢复的上限132/84/36/768，加两卡合计14400 GPU lease秒。每job预留7200秒，6500运行timeout+600清理+100 pre/post/reap余量=7200。首批两根的18格包含在正式规划中，不能再额外计数。旧708/708/540、37620 solver、383400 GPU秒明确仅历史提案，不是当前派发授权。

首波manifest与两份child authorization在检查时均为false，CPU检查没有将其改为true。350GiB仍为空间规划、个人quota未保证；24GiB/worker是规划RAM allowance，peak RSS未实测。此次核对不批准任何物理资源额度。


最后scene定向修复：跨split近重复比较只基于任务主体/设施/目标角色，移动similar/background/marker不能单独绕过检查。新增独立反例对F1–F4分别仅移动这些背景角色，四族near_duplicate均仍为true。生成器相应在不同split采用实际任务布局变化，reserve在继承split/difficulty后采用同split区域。修复后独立21+scene8、F4资格/工厂10+F2/F3参数绑定3重新通过；不会把这些CPU几何差异宣称为已经实测物理可达或统计独立。


## 最终窄补充：配置文件原始字节与完整程序定义

Launcher新增`spec_file_sha256`与`authorization_file_sha256`，在预检、租用前、child前与完成验收时读取并核对同一份被哈希的字节。独立复跑9项launcher测试全部通过；即使重新签署内部spec hash，改scene配置或改合法copy destination仍会在首次GPU snapshot之前拒绝。

`validate_resolved`现在比较完整预注册program steps，而不只比较program IDs。新增独立反例在F1–F4分别保留ID、篡改第一步主体并重算spec self-hash，四族均拒绝。独立套件最终22/22通过，其中统一CLI正例再次贯穿最终冻结源的完整F1九格验收和自动copy。

此次仅两个窄修复新增2项测试，最终总数79；其他此前通过的套件/物理待验证边界不变。最终693个运行文件源锁：`dfbb2fd48a195d147939bcfd4e1790ecf1db5cd917249cc7df67a239a18c04fb`。由主协调者用这一版本刷新最终manifest/authorization文件hash及source pin；本检查没有修改授权标志。


## 最终交付复核：全部文件绑定已对齐

最后计量修复之后，launcher9/9再次通过。`collection_attempts`按实际cleanup中已创建的`strict_prefix_branch:`场景计数；采图或prefix阶段即失败、尚未执行suffix也计一次采集尝试。缺失phase信息保持usage unresolved，不猜测为零。这项是现有回归补强，总测试数仍为79。

独立重新核对全部693文件inventory、`SOURCE_FREEZE.json`、首波manifest source pin、两份child authorization source pin、每job spec_file_sha256和authorization_file_sha256，全部一致；manifest与两份child授权仍为false。计划重新生成与PLANNED_SLOTS_V2完全一致，首波两个spec也与生成器输出一致。此前报告提示的旧pin未刷新事项已经解决。

最终运行源锁：`dfbb2fd48a195d147939bcfd4e1790ecf1db5cd917249cc7df67a239a18c04fb`。

另独立使用实际四包中新追加的`reader_final_20260910.py`重新读取，安装audit hook禁止访问原datasets、active RoboTwin与Vault；四包均通过，state76，future分别4203/4189/5508/12018×26，target仍不在inputs。四份最终reader字节SHA统一为`e0e6587e819014f0bebecc68b0653ab00edaa369e06f0cf8b65ffa2e1a9c4f5d`。上文旧reader hashes保留为第一次独立读取记录，不冒充最终reader版本；原raw/receipt/原包manifest没有被改写，新reader以独立upgrade manifest追加。

最终结论维持`CPU_RUNTIME_READY / FIRST_WAVE_PHYSICS_PENDING`。本独立检查没有遗留已复现未解决的交付阻断项；新GPU授权、调度解释和真实首波验证仍不在本次CPU检查的成功声明中。
