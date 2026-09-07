# F2 on/beside 独立 suffix CPU 实现

入口 `runtime.run(scene,replay,relation=...,output=...,current_sha256=...,initial_anchor_sha256=...,initial_anchor_equivalence=...)`。
调用方负责真实 fresh scene、原 canonical replay、live Goal meter、UUID Guard、cleanup 和整个 root Gate。
本目录不创建场景、不签清单、不写总账、不接受 root，也不读取或恢复旧 held-state。

两条路线均为持物2段→原 held transport Gate→full-open→100帧→实际 static-can/open-joints fullworld→退回2段→75帧→原最终关系 Gate。
on 保留 metadata/functional-point 目标、100mm预放和原 footprint/高度/支撑/排他门；未批准任何 scale 碰撞例外。
beside 保留已审查 D actor target 和47.946915502860445mm预放，实际 replay 抓持变换决定 EEF 目标；不使用旧80mm或6段。
每次持物规划前重新拟合实际抓持，beside仅限实际原 table__0 支撑证书和 can/table pair，机器人及其余world全保留。
全路径逐sample native can/world筛查，只有beside/table允许原0.1mm native数值接触带；不证明连续sweep或物理成功。
真实释放100帧后重新捕获can和全部actual named joints，不用预计D/open qpos，不瞬移can。

suffix上限4个实际MotionGen问题、0独立IK、0新建场景/collection（包含场景及实际action由外层计）。
高层模型start检查：on正常6次；beside正常10次。这些不是solver问题，也不是whole-root预算。
复用inside live_models仅Base实际fit/query/几何映射及纯released_config_and_world；不调用其floor/inside门或5-query spec。
原held/final verifier从冻结active `family_runners_v3_3.py` AST提取原语句执行，未修改原source或数值门。

未执行GPU；CPU synthetic tests不构成on/beside资格或新pilot接受。若on fullworld因scale失败，停止并提交scope review，不能自动加例外。
