# 五项定向修复与适用边界

本轮依据t_6aa24e26，基线11b34925a607b92987b233cb50a4cd3fe3950852。原数据、预算、历史接受与四族迁移小样保留；这里只修改新F1正式入口及其必要共享CPU验收/副本接口。

| 问题 | 实际修复位置 | 可检查的变化 | 验证入口 |
|---|---|---|---|
| 正式阈值/物理/变体同义 | `f1_disk_verifier.py`、`native_f1.py`、`scene_plan.py` | canonical D6.6/6.7把非目标移动阈值交由Stage2冻结，本版spec已有3mm；旧provisional10mm用于同一whole-trace/t0信号，因此正式入口读取3mm，明确阶段/单位/frame，无隐式fallback。实际关节开度、robot-link分离、完整接触及支撑几何联合验收；path仅比较safe_horizontal运输段，motion核注册post-prefix hold及控制数组。 | VERIFIER_CELL_REPORT.md与定向负例 |
| 逐cell立即独立验收 | `family_entry.finalize_native_cell`、原生orchestrator完成路径 | capture写入读回在动作前；raw保存和安全收尾后，磁盘完整性、身份、row0、真实语义/阶段、模型出口先检查，再允许下个cell；跨分支条件留root层。 | 真实save/finalizer/export集成，缺RGB停止 |
| 真正可达的有界恢复 | `first_wave_launcher.py`、`execution_cli.py`、`f1_full_production.py` | 显式resume、有限attempt及全族/每root剩余cap，原成功文件hash和独立重验，实际只跑缺失cell；copy-only无backend/lease/scene。源变更使用reviewed compatibility附录，原manifest和ledger不变。 | LAUNCHER_RECOVERY_REPORT.md |
| anchor等价与副本一致 | `anchor_equivalence.py`、`portable_v2.py`、`f1_portable_export.py` | 单文件源/副本SHA严格一致；跨cell按相同版本化物理字段/容差和数组比较。保留每条capture，不改写统一anchor；包带独立规则、common reader和语义目录。 | COPY_ANCHOR_REPORT.md |
| 异常lease证据 | 当前launcher | acquire后立即保存主机/时钟/UUID/job/attempt；child、cleanup、release与未证实状态独立落盘，之后才usage/settle/copy。未知不估计，已测时间可幂等对账；busy无child不计物理尝试。 | acquisition/state/post/parser/settle/release/中断故障注入 |

两处直接相关的额外接线问题同时修正：

- F1辅助object_pose固定为红色，不能用于判断绿/蓝主体；独立语义改读对应role_object_pose及实际接触身份。
- 原生adapter的implementation_source_sha256与完整source/config bundle是不同算法与范围；新包分别冻结，禁止拿全bundle冒充原生实现锁。机器人/相机/solver配置、URDF/SRDF及其mesh也进入文件hash清单。

全族计划、状态机、预算与最终发布另见PRODUCTION_PLAN和唯一Luna交接。最终CPU测试与第二轮检查结果以CPU_VALIDATION和独立报告为准；不能用此说明代替真实运行。

保留限制：原生新场景物理可达、实际相机/渲染、抓取/接触与运行资源峰值需要未来授权后的真实首批及逐root检查。本轮不把synthetic CPU成功写成正式物理成功，也不把90格计划写成90条已采集。
