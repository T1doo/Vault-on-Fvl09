# F1_000013 motion-only recovery CPU closure

本包依据用户提供的 GPT 审阅条件建立，范围固定为已有 `F1_000013` 六格保留证据补三格 `r_inv_motion`。旧 `formal_f1_full_v1` root、旧 STATE、旧 ledger、旧 raw 和旧回执保持不变；执行输出位于独立恢复副本。

## 三项收口

- motion 在 35 帧 `S_prefix → S_motion_start` hold 后，只加载同 root、同 program 的已封存 `r_pc` suffix artifact；没有 live suffix replanning。baseline manifest、数组、execution spec、prefix hash 和起点 qpos 均校验，起点超过 1e-3 rad 则不执行。
- launcher 以当前 attempt 前后 pointer/terminal 回执的字节变化建立 `current_attempt_evidence`，历史 root/recovery 回执只列入 `root_history`，不参与本次分类或 reserve 资格；reserve eligibility 还要求不同 attempt ID 的隔离物理证据。
- F1 `verify_f1_disk` 与 `verify_variant_pair` 的实际 JSON 读取显式使用 UTF-8，并在 `LC_ALL=C`, `PYTHONUTF8=0`, `PYTHONCOERCECLOCALE=0` 子进程中验证中文 manifest 路径。

## CPU 证据

- `test_f1_verifier_cell.py`: 11/11；包含实际 motion hold 正例、单值 non-hold 控制反例、三程序 baseline artifact 校验和 ASCII locale 真实 `verify_variant_pair`。
- `test_first_wave_launcher.py`: 12/12；包含旧物理失败与当前无终端、旧工程失败与当前物理失败的交叉隔离。
- `test_family_entry.py`: 14/14；已有完整 F1 synthetic 链保持结构保护。
- 既有全 discovery 结果仍如实登记 138/140：两项是范围外 F4 synthetic fixture 复用 F1 专属合同的错误；本轮不修改 F4 fixture、不运行 F4 物理。
- 实际 `execution_cli` 授权边界 probe 在 GPU 授权为 false 时返回 `PermissionError`，没有创建输出、没有 native scene、没有 GPU snapshot。

## 恢复边界

manifest：`/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/manifest.json`
authorization：`/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910/F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911/specs/F1_000013.authorization.json`
state：`/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911/recovery_state/STATE.json`
ledger：`/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911/recovery_state/execution_ledger.jsonl`（首始为空；当前 4 events，consumed 仅 GPU lease 3 秒，reserved 全 0；两段 contract amendment 保留 ancestry）

预算上限一次性固定为 fresh=11、action=7、collection=3、solver=64、GPU lease=7200 秒；只允许 `F1_000013`，只允许缺失的三条 motion，original primary slot 为 `F1_000001`。执行时一张 Guard 通过且独立空闲的 GPU，三条依次执行；不重跑旧六条、不转其他 root、不扩展 reserve。

当前 CPU 状态已满足条件式恢复授权，尚未启动本恢复包的 GPU/物理执行。


## 实际尝试收尾

第一 attempt 在 GPU0（`GPU-2c620e6c-9639-2022-b573-9847dfa33769`）获得 3 秒 lease，因复制副本中历史 compatibility 文件冲突在 native 场景前退出，新增物理场景、动作和 collection 均为 0；owned cleanup、释放和 post snapshot 均通过。修订 timeout 后的第二物理启动在自动审批层被拒绝，命令未执行、没有新 lease。新 ledger 保留首个 attempt 并追加 parent-contract amendment，当前 consumed 仅 GPU lease 3 秒、reserved 全 0。

自动审批拒绝后，本物理恢复保持暂停；继续执行需要用户确认修订后的 timeout/manifest/ledger 合同。


## 实际恢复副本预检

已在 GPU 前调用真实恢复副本的六条 `validate_saved_cell` 与 `export_native_cell`：6/6 通过。副本内 current/anchor/capture 字节复制后 hash 一致，raw manifest 的 capture provenance 已指向副本内路径；原 formal root 的 capture/current/anchor/raw/receipt 均未修改。canonical prefix 和三个已封存 `r_pc` suffix artifact 均按 root/program/source/数组绑定加载通过，checkpoint 仅保留 `r_inv_motion` 未完成，recovery request 仅请求三条 motion。预检回执：`ACTUAL_RECOVERY_CPU_PREFLIGHT.json`。


## attempt 2 的无物理改卡规则

attempt 1 没有物理场景、动作、collection 或 solver 消耗，GPU0 后续被外部进程占用时，当前恢复合同允许 Guard 从 GPU1–6 中选择实时独立空闲卡；这不是 root 内分片，也不允许物理执行后换卡。该规则由 `GPU_REBIND_PREPHYSICAL_AMENDMENT.json` 绑定，预算与 attempt 3 禁止条件不变。


## attempt 2 实际收尾

attempt 2 在 Guard 选择 GPU1（`GPU-414c52ba-72c6-fc45-95d6-1e9750bbc21b`）并获得 3 秒 lease，但在 native 场景创建前因 authorization compatibility SHA 滞后退出；physical scene/action/solver/collection 均为 0。GPU child、lease 和 cleanup 已结清，累计 recovery lease 为 6 秒，reserved 全 0。修复后的授权绑定已封存，状态等待用户是否单独允许 attempt 3；不会自动启动。
