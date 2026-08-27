# F2 beside reference pot audit v2

两个 display-stand sectors 均发生 place planner failure 后，按预定流程审计官方 pot fallback。该 fallback 不改变 F2 的共同 main object：仍固定 `071_can/base1 + left arm + beside`。

## 官方来源与区别

- 官方 env：`envs/move_can_pot.py`，class=`move_can_pot`。
- 官方 reference：`060_kitchenpot`，model IDs 0–6；选择 base0（目录 `100015`）。
- 官方 left-side target rule：`pot_x - 0.18, pot_y, table_z`。
- 官方任务原 main object 是不同的 `105_sauce-can`；本项目不会复用它，也不会让三个 F2 branches 使用不同 can。

## 联合场景 wrapper

pot 放在 `(0.18, 0.02)`；`071_can/base1` 的 provisional target center 为 `(0.0, 0.02, 0.79)`。该 target 到 box/scale/pot center 的 XY 距离分别约 `0.255/0.190/0.180 m`。pot 使用 fixed root，明确标为 project wrapper，用于避免三关系共同场景中的 dynamic reference drift；不冒充官方原任务的 dynamic body 配置。

CPU audit 与 20/20 tests 已通过；GPU `pot_left` probe 尚未运行。JSON 中保存 source/asset hashes、尺寸、clearance 和 provisional predicate。
