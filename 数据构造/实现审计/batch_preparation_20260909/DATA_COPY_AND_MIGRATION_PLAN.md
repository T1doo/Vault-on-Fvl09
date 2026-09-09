# 独立副本与迁移方案

已建立`/nfs_share/lijunhui/CVPR_FutureIntent_Data/`，该目录此前不存在；本轮仅复制一个已通过cell，原目录不动，不使用软/硬链接，不进入Vault或RoboTwin Git。底层NFS与原数据同卷，这是独立文件副本，不是异地或硬件故障备份。

## 可迁移小样的实际结果

`reference/p4_v1/F2/F2-A-v2/beside/r_pc/`含原trace、四路t0 RGB、state、anchor、capture、prefix、cell/root receipt和独立finalizer、F2-A reconciliation、资格索引以及派生supervision。复制约129,209,055 bytes（13项含监督）；copy阶段约2.98s，仅是单cell热缓存读写样本，不能推断全量吞吐。

`MIGRATION_SAMPLE_RESULT.json`记录从新包读取成功：四路240×320×3 RGB、state76、future4189×26、三候选。审计hook明确拒绝访问原datasets、active项目和Vault文件，reader只给包目录；不靠删除/改名原目录模拟迁移。reader使用NumPy和标准库，无SAPIEN/CUDA依赖。占位action row0剔除一次，N actions/N+1 states检查通过；target只在supervision。

原文件字节不变，portable_manifest存original_path、relative_copy_path、SHA256、source ID和角色；原receipt的绝对路径保留为audit。tools/portable.py是仅支持本轮F2-A beside小样的最小工具，不宣称四族完整生产导出器；六个CPU测试涵盖计划唯一性、缺realization、虚构观测hash、路径逃逸及副本丢失/损坏。

## 正式包结构与发布

```
CVPR_FutureIntent_Data/
  reference/p4_v1/F2/F2-A-v2/beside/r_pc/   # 本轮已复制
  releases/formal_v1/F2/F2_000001/
    group_manifest.json
    common/                                # candidates/spec/prefix及验收
    intent01_inside/{r_pc,r_inv_path,r_inv_motion}/
    intent02_on/...
    intent03_beside/...
  _staging/                                # 未完成、不可对外发布
  manifests/                               # source→relative copy映射/终端
```

每条capture保留原文件、身份和比较证据；即使以后按内容去重，也须保留24/9次真实capture映射，不以一张规范图替代来源。inputs只有RGB/state/future/candidates，supervision包含target/compatible set（未来H视图需按observable语义产生，不能从本整段target外推所有H），audit存隐藏物理真值、verifier和来源。视频可选。

每个root封存→staging物理复制→逐文件hash及必要依赖/读取检查→同NFS原子rename发布→登记manifest与copy terminal。中断文件用.partial，恢复先核原源封存SHA，已匹配文件复用；源改变即停副本发布。复制故障只影响归档完成，不撤销物理成功、更不重跑机器人。禁止rsync --delete和移动源。正式工具后续须扩展按root锁、fsync目录/终端、幂等发布及故障注入；当前小样已验证复制/校验/无原路径读回，未证明整族崩溃恢复。

## 空间实测与规划

统计范围为索引明确引用的有效trace/current/receipt与F1/F4 raw目录；不是全工作区du。见STORAGE_INVENTORY.json，唯一文件与重复引用分开。当前48条有效引用合计约11.37GB，视频未计入。

| 族 | 12条唯一相关文件bytes | 平均trace MB | 最大NPZ解压成员合计GB |
|---|---:|---:|---:|
| F1 | 2,143,304,936 | 88.50 | 3.26 |
| F2 | 1,473,322,034 | 122.41 | 4.87 |
| F3 | 1,575,477,529 | 130.92 | 4.33 |
| F4 | 6,180,898,980 | 252.54 | 8.27 |

NPZ磁盘已压缩，zip成员合计是完整解压上界，不等于reader同时加载峰值；本reader只加载必要数组。按每族90条线性估算约85.3GB单份；原件+副本约170.6GB。16reserve最多144条另留约34.1GB单份、两份68.2GB；36个恢复失败cell按每条.52GB上界留18.7GB；copy staging最多两root约9.4GB；CPU解压/检查2worker约16.6GB；以上合计约283.5GB，另加25%余量约354.4GB，建议预留350GiB（约375.8GB）。这不是实际将写满的预算，也不包含旧全历史与未来高清视频。

共享文件系统查询时可用约27.35TB、inode可用约534亿；均为共享卷信息。quota命令因设备视图缺失失败，个人配额/硬限制未知，不能据df宣布350GiB配额已保证。首波前须确认可分配配额至少350GiB或重新按批准范围拆分释放计划；本轮小样写盘已成功。只读取元数据和有效文件，不递归全历史。

## 两种迁移

A离线使用：拷走本cell目录及reader，安装NumPy后运行`python reader.py read .`即可，任何原目录路径都不用于读取。formal版本需类似root包加总索引与split；当前仅1cell已复制，其他47条仍为引用/待复制，正式releases为空。

B重新仿真：另提供采集时source snapshot、准确asset mesh/material/scale及哈希、机器人URDF/SRDF、相机/render配置、物性/settle/rest说明、Python/SAPIEN/CuRobo/CUDA版本。v43只能作收口参考，不能替代原job源码锁。单cell已含source scene spec和anchor但未复制所有仿真资产，未验证重仿真可迁移；不复制整个conda、凭据或无关目录。
