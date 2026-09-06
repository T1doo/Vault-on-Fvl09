# 已有 18 格独立复用资格核验

2026-09-07，CPU-only。范围：F1-A、F1-B、F4-A 各 6 格；不产生数据、不改原 artifact、不签发 Stage 1 接受。

`audit.json`：18/18 通过。重新读取实际磁盘 raw/trace/video 并计算哈希，重跑既有 root finalizer 与 F4 六轨迹最终状态等价检查。额外逐条载入 NPZ，检查 N 个 26 维 actions、N+1 个状态、250 Hz 和 action 区间前后端点对齐及数值合同；所有 raw 初始 qpos/qvel 与 trace row0 一致。对全部 18 条验证共享 current 的 lossless 38+38 状态、三路 RGB、夹爪哈希，不使用未来状态。

`resolution_audit.json` 单独重算 F4 append-only resolution 与 F1 UTF-8 failure recovery 的全部列出原始文件、派生回执及 reconciliation 哈希。原失败终端保留，不把失败抹掉。

结论：这些 18 格可由主调度者在本次 8 roots / 48 pilot 目标中显式复用，无需重跑。它们是 3 个根，不是 18 个独立根。此报告仅提供资格证据，不冒充 Stage 1 科学 Gate、formal 360 或训练授权。

覆盖边界：未创建模拟场景，未视觉观看视频；视频使用真实文件哈希和既有合法 verifier/receipt。历史 cleanup 的回执链已核验，不把它说成此刻的新 GPU post-check。物理 family verifier 未逐个重放，使用哈希绑定的原结果和重算 root finalization。

复现命令：使用项目 Python，设置 `PYTHONDONTWRITEBYTECODE=1` 与 workspace 内的 MPLCONFIGDIR/TMPDIR/XDG_CACHE_HOME，`timeout 900 .../python audit.py`。写出采用 exclusive UTF-8；已存在报告不能覆盖，复核应使用新命名空间。首次裸 `python` 不在 PATH（exit 127，无写出），实际核验已切换项目绝对 Python 路径完成。
