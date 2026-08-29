# F1–F4 implementation registry — runtime-v3_2 current

## 当前映射

| Family | Objects / facilities | Arm | 当前证据状态 |
|---|---|---|---|
| F1 | project RGB red/green/blue blocks；`062_plasticbox/base3` | left | task/physical 3/3；red/green planner pass；blue terminal fail |
| F2 | `071_can/base1`；`062_plasticbox/base2`；scale/base0；stand/base3 | left | 三关系 planner 可行；beside accepted；inside/on/root fail |
| F3 | `001_bottle/base13`；pad-support-v2；table-z V / table-x H | left | grasp-lift pass；三个完整 raw；semantic/root fail |
| F4 | `008_tray/base0`；yellow X；RGB A/B/C；visible slots | right | common-X pass；ABC/ACB/BAC target construction fail |

## 当前实现合同

- official baseline 不修改；全部项目代码位于 additive `controlled_multi_future/`。
- candidate universe、task tree 与 canonical prefix 在 planner rollout 前冻结。
- task/physical feasibility 不由 planner success 定义。
- 每次审计和 rollout 使用 fresh scene，并保存 scene-bound cleanup receipt。
- primary raw 为 26-D / 250 Hz / N+1；requested、effective、planner goal、realized state、contact/verifier 分流。
- current/anchor、source/assets/config/environment、authorization、GPU index/UUID、timeout、command 与 output namespace 均有 hash binding。
- 执行异常保存 partial trace；最终 receipt 失败时 append-only root events 仍保留证据。

当前状态为 `BLOCKED_WITH_REASONS`。确切 code hashes、final namespace、repair counts、guard/cleanup audit 和 blockers 见同名 JSON。
