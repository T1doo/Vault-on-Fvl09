# Luna：F1全族生产交接

本包替代“只准备首两root”的任务终点。当前仅CPU准备，所有实际执行授权为false；本文件不是GPU授权。保留旧pilot和所有历史预算，不向旧Goal续写余额。

目标是F1十个有效root，每个三意图×三realization，共90条及独立副本。四个有序reserve只替换失败的主槽位，不增加目标分母。首18条属于90条；未来用户一次批准全族范围和总预算后，首18条为程序自动检查点，通过即继续72条。F1完成后停止，不派发F2/F3/F4，不训练、不H-reveal、不压缩、不渲染HD。

## 从这里开始

1. 读工作区AGENTS.md与本文件，检查Git status及`数据构造/F2F3重设计与构造日志.md`尾部，保护并发修改。
2. 读本目录`FIX_CLOSURE.md`、`PRODUCTION_PLAN.md`、`F1_BUDGET_REQUEST.json`、`STORAGE_PLAN.json`、`CPU_VALIDATION.md`及`INDEPENDENT_REVIEW.md`。
3. 使用项目Python和明确PYTHONPATH。不要使用旧`F1_FIRST_WAVE/manifest.json`，其源锁属于前一版历史。

```sh
cd /nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910
export PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin
export PYTHONDONTWRITEBYTECODE=1
/nfs_share/lijunhui/Robotwin2/env/bin/python f1_full_production.py preflight
```

CPU预检验证十个具体spec、90格、源码/资产文件、正式F1阈值和预算。它不证明相机原生采集、新场景可达、抓取接触或实际耗时。不得把`prepare`当成随意更新源锁以绕过已批准包的办法。

## 唯一授权范围与预算

用户需一次确认：全F1十主四备、90条目标、统一总cap及有限恢复。未确认前不得启动。

| 资源 | 十主正常 | 十主恢复余量 | 四备正常 | 四备恢复余量 | 全族cap |
|---|---:|---:|---:|---:|---:|
| fresh scenes |330|330|132|132|924|
| action scenes |210|210|84|84|588|
| collection attempts |90|90|36|36|252|
| solver problems |1920|1920|768|768|5376|
| GPU lease秒 |72000|72000|28800|28800|201600|

GPU时间为保守上限（56 GPU小时），不是实测耗时或完成时间承诺。正常无恢复每root33fresh/21action/9collection/192solver；三个cohort分别资格与采集，公共前缀不是免费附带。每root至多两个GPU attempt，共享物理cap66/42/18/384；每attempt最多7200秒（6500运行+600清理+100检查），root累计GPU cap14400秒。已成功cell恢复不重执行，但重新资格成本照计。CLI无场景错误只计可靠测得的lease，不按整个预留核销。未知耗用保留未决，不伪造结束时间。

并发上限：2 GPU jobs、2 CPU finalizers、1 copy worker。每root固定一张当时独立idle的GPU0–7；使用已有Guard、UUID锁、项目CUDA和独立cache/TMP。全部wave/attempt共用同一账本。copy在GPU释放结算后执行。

## 将未来批准封存为新包

保留当前false提案。收到明确批准后，新建批准记录，包含`decision=APPROVE_FULL_F1_90`、当前提案manifest文件SHA256、完整budget_caps及用户指令引用。不要由程序自行创造批准。

```sh
/nfs_share/lijunhui/Robotwin2/env/bin/python f1_full_production.py seal-approval \
  --package F1_FULL_PRODUCTION \
  --approval-file /nfs_share/lijunhui/Robotwin2/datasets/f1_full_user_approval.json \
  --approved-destination /nfs_share/lijunhui/Robotwin2/datasets/f1_full_approved_package
```

该命令核对明确的整族批准，重新封存授权文件及其hash，并保留false提案原件。它不启动GPU。正式启动：

```sh
/nfs_share/lijunhui/Robotwin2/env/bin/python f1_full_production.py run \
  --package /nfs_share/lijunhui/Robotwin2/datasets/f1_full_approved_package \
  --state-dir /nfs_share/lijunhui/Robotwin2/datasets/formal_f1_full_v1_state
```

## 连续推进与恢复

协调者消费全部十个主root。首批两个train root的逐cell检查、完整9/9、原件和副本及资源结清后，自动记录`FIRST_18_AUTOMATIC_GATE_PASSED`并进入八root队列；无需新人工批准。当前初始派发采用保守的首root门，绝不让第二root绕过共享错误。

若只有忙卡，不占卡也不收费；等待后重复同一run命令，仍使用原STATE/ledger。普通物理不可行或已分类临时执行失败，在额度和次数内恢复缺失cell；超出上限才按完整terminal barrier、原主槽rank分配reserve。不得因worker结束顺序改备用分配。reserve激活后继承split/difficulty，未激活只保留planned slot，不伪造current/anchor/prefix。

已通过root仅copy/索引失败，走CPU-only恢复，原采集不重跑。源版本冲突、共享观测/字段/验收错误、耗用未知、owned cleanup不明或BUDGET_OVERRUN停止新派发，保留在途安全收尾及证据。不能删除FAILED、清空输出、重建账本或更换task ID绕过上限。

源码变更必须逐项审查受影响合同与已通过文件，保留旧源锁及原字节；不能默认兼容，也不能直接判全部重采。validation/test结果不能用于调配方后仍宣称untouched；发生这种情况记录访问与污染影响，停止受影响正式资格。

## 数据与完成检查

原始目录：`/nfs_share/lijunhui/Robotwin2/datasets/formal_f1_full_v1/<root>`。
独立副本：`/nfs_share/lijunhui/CVPR_FutureIntent_Data/releases/formal_v1/F1/<root>`。

副本为`common/`及`intent01_red|intent02_green|intent03_blue/r_pc|r_inv_path|r_inv_motion`。每格保留实际current、anchor、输入/监督/audit分流及来源。原件与副本逐文件SHA一致；跨cell anchor按统一物理等价规则，不能强求JSON文件SHA一致。包内reader不访问原目录。相同NFS第二份文件不等于异地备份。

最终需十个不同有效root替代十个主槽、90个唯一cell，split/difficulty和reserve链正确，全部独立验收与副本可读，`FAMILY_MANIFEST.json`和`dataset_index.csv`匹配，总账reserved为0且无自身残留。完整输入不自动等于科学Stage1/Temporal Gate通过。

Luna最后追加日志、汇总失败分母/资源和资格，单一发布者commit/push私有Vault/main并核对远端SHA，向用户交回F1结果。

## 只恢复证据或副本的命令

完整采集已通过但复制失败时，可直接使用同一个全族账本的CPU入口；以下命令不会构造GPU backend：

```sh
/nfs_share/lijunhui/Robotwin2/env/bin/python first_wave_launcher.py \
  --manifest /nfs_share/lijunhui/Robotwin2/datasets/f1_full_approved_package/manifest.json \
  --state-dir /nfs_share/lijunhui/Robotwin2/datasets/formal_f1_full_v1_state/launcher \
  --copy-only-job full_F1_000001
```

若child和lease结束的可靠原件已保存，但usage解析、settle或总状态发布失败，先用同入口的`--reconcile-only`做CPU幂等对账。它只认真实已保存的cleanup/release/时钟证据；若缺少这些证据会拒绝，不填造结束时间、不直接核销整个预留。对账后再运行全族入口。

源码修复后的恢复附录不是重新批准全族预算：在已授权CPU修复范围内，记录旧/新source bundle、全部changed files与逐项affected-contract审查、每个适用job的新授权绑定、成功原件hash及CPU重验；原manifest/ledger总cap不变。用`first_wave_launcher.validate_compatibility`验证，随后全族run增加`--compatibility-file <附录路径>`。全族入口要求全部十个主job明确列为适用，已激活备用也需绑定；未列明的旧source job不会自动运行。物理/语义spec变化不属于source-only附录，停止并提交一次集中影响说明。

compatibility中明确修复的共享错误，必须有绑定新source的通过证据，才能恢复，且原attempt/root cap仍然有效。旧成功cell经真实磁盘raw/current/anchor/语义/出口重验后才可复用，原字节不改；不能用一张`pass=true`回执跳过这些检查。

预算的更紧调用链核对：在“每root最多两个实际child、首个未接受cell立即停、成功cohort/cell复用、无额外qualification或第三次attempt”的当前实现下，每root最多42fresh/26action/10collection/256solver；14个可能执行root合计588/364/140/3584。上表924/588/252/5376保留更宽的管理cap，不能称为必需消耗或耗时预测。实耗按原件逐attempt增量结算；无child的busy阻断只可能增加已实际取得lease的时间，不增加物理四项。更紧分析不另开预算，也不允许第三次物理attempt。
