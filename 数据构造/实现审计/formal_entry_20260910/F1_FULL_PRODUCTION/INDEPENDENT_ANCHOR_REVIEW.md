# 第二轮独立复核：anchor 与副本

范围严格限定本轮 `anchor_equivalence.py`、`portable_v2.py`、`f1_portable_export.py` 的文件完整性、跨 cell 物理等价、来源绑定和副本恢复。只读检查运行代码；仅在隔离 CPU fixture 中复制/改变测试文件。未调用 GPU、未检查所有旧历史、未改原始数据。

## 已直接核实

1. **单文件完整性与跨 cell 等价已分开。** adapter 在解析 source 前核 expected index SHA 和文件 SHA；复制前后、复制文件、再次读包均核对同一索引。F1 anchor 跨 cell 使用版本化物理规则，不要求九个 anchor JSON 文件 hash 相等；RGB 与 r_pc prefix 比较解码后 key/dtype/shape/数组字节，允许不同 NPZ 压缩封装。
2. **物理规则不会因 source compatibility 全面放宽。** qpos/qvel/drive、gripper、角色集合、pose、速度、sleep、物性配置等仍按同一白名单/容差或精确规则检查。来源例外只允许已审定 old/new bundle 对与列入 accepted_cells 的旧 capture，且 physics_config 仅 implementation_source_sha256 可按明确映射改变。改变 dt 的反例仍失败。
3. **副本保留原件且可独立读取。** normalized capture 与实际 native capture 的绑定字段/哈希交叉检查；native anchor 与副本 anchor 必须逐文件相同。包内包含 reader、anchor helper 与合同。独立子进程禁止打开原 source 与中间 cell 目录后，仍从发布 root 的 bundled reader 读到九格。
4. **发布与恢复有直接故障覆盖。** intentXX_identity/realization 目录来自候选语义。cell/root staging、文件校验、rename、registry 分步处理；copy_mid、rename 前后、index 故障和重复调用通过，源文件版本冲突拒绝，原源文件 hash 保持。恢复不调用机器人或 collector。

独立执行：

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910 \
/nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest \
  test_anchor_copy_v1.AnchorTests test_anchor_copy_v1.CopyTests \
  test_portable_v2.PortableTests test_formal_export.ExportTests -v
```

结果：18 项通过，32.868 秒。这里没有把 owner 的通过声明作为本次执行结果。

## 直接发现的一项阻断

修复前 `portable_v2.read_root` 核对 group/root 两份镜像和 nested cell 哈希，但没有把根头的 root_id/family/spec/candidates 与实际 nested manifests 对账。

隔离复现：先正常发布九格 `F1_fixture`，保持 source index、九个 cell 和所有数据文件不变，只把 `group_manifest.json` 与 `root_manifest.json` 的 root_id 同时改为 `F1_wrong_root`。`read_root` 未拒绝，返回的 root_id 为 F1_wrong_root，而 cells 的真实前缀仍为 F1_fixture。

这直接涉及本轮“错 root 必须拒绝”，不是另加审计范围。已交主协调者/owner，限定补根头与 nested 的绑定及定向反例；建议同时让 synthetic 标记与实际 nested 一致，防止根头将 fixture 改称非 synthetic。

该项为初次审阅时实际未关闭的缺口；随后由 owner 定向修复，独立复核结果见下节。

## 本次读取时的源码字节

- `anchor_equivalence.py`：`2a2f33aed4ec48e3dd949766e9f55d45c3ca5f58b46fd5e5bad18b37f16542ff`
- `portable_v2.py`：`affe90282f66d6740af970191da03d2e9cbbb2f4f64479a67df3621c21a9095c`
- `f1_portable_export.py`：`bda1104d275283b0dda140cc16c866dff60890842ece9dfcd4afb01baac96bde`

## 修复后定向复核

已关闭。只复查原身份反例及同类根头字段，未扩大范围。读取修后 `read_root` 确认：root_id、family、scene_spec_sha256、candidates 必须逐项等于 nested manifests 的共同值；synthetic 必须等于实际 nested 标记；当前复制 schema 不允许根头单独设置 formal_eligible=true。audit-only 的历史绝对 root 路径仍不作为迁移后的读取位置要求。

我独立执行：

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910 \
/nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest \
  test_anchor_copy_v1.CopyTests.test_root_headers_bind_nested_identity_and_qualification -v
```

结果：1 项定向测试通过，4.283 秒，其中分别同步篡改两份根 manifest 的六个字段均被拒绝，恢复原字段后可正常读取。修后 `portable_v2.py` SHA256 为 `c818c9eb5a19bd9d8c07f1cb8ccf850e5a3bee91f7d566c9c996fc030d40f6f3`。

**限定结论：本轮 anchor/副本审查通过，发现的单一根头身份缺口已按直接反例修复关闭。** 这支持 CPU 副本接口准备完成，不证明未运行场景的物理成功，也不替代原始采集、全族验收或 GPU 授权。
