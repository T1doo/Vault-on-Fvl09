# Post-Gate CPU root-cause audit and next proposals V1

日期：2026-09-03  
状态：`PROPOSALS_ONLY_NOT_AUTHORIZATION`

## F2：从抓取微门升级到一个development root

F2已有两个真实top-contact成功。下一步不再搜姿态，而是固定与family左臂contract一致的第一个成功候选：

- scene assets：`can0 + box2 + scale0 + stand0`；
- arm/contact/rotation：`left / 8 / 0`；
- recipe：`f2-final-grasp-v2-r000725`，SHA=`f7270daf416afb1b84e230be7dd2418ac0e5a31d2461943da3bd77c6777cfe5e`；
- source physical scene receipt=`c3ac8155fcff909383c2ed72fe178edc10d4ca66a541a3a9b5d5f765f991bc47`。

提案只允许一个三program `r_pc` development root：同一current/anchor、同一精确pregrasp/grasp/close/12cm lift prefix，然后分支到`inside/on/beside`。全部现有suffix target、threshold、release-safety和family verifier保持不变。上限=`75 planner / 8 fresh scenes / 4 robot-action scenes / 3 branches / 3 raw+MP4 / 1 development root / 3 development trajectories / 0 formal`；任一失败原子终止，无fallback/retry/第二root。Proposal SHA=`56c326af064260865ef0c3d8f2c217ff21158af8f9bef5684ba6e8a79a308723`。

## F3：rotation1不是有效修复

rotation0→rotation1只把四个pregrasp沿y方向移动约21 mm。因此：

- `bottle5-right-lower`仍在x=0.388m的外侧，报`FINETUNE_TRAJOPT_FAIL`；
- `bottle4-left-upper`仍在y=0.100m，报`IK_FAIL`；
- `bottle13-right-upper`仍在x=0.382m外侧，报`FINETUNE_TRAJOPT_FAIL`。

CPU从已实现的official contact frame、`rotate_lim=[0,1]`与`ROTATE_NUM=10`重建每个失败stratum的80个contact×rotation目标，然后按固定的`min |x|+|y|`中心性规则选出：

| Failed stratum | Proposed tuple | Recipe | 重建pregrasp xyz (m) |
|---|---|---|---|
| bottle5-right-lower | contact2/rotation1 | `r1505` / `88f1c0bc…` | `[-0.029365,-0.008158,0.785575]` |
| bottle4-left-upper | contact0/rotation6 | `r2180` / `176bc2a1…` | `[-0.006834,0.002679,0.783888]` |
| bottle13-right-upper | contact2/rotation5 | `r3677` / `3d945ce1…` | `[-0.007234,-0.001372,0.757185]` |

保留已通过的`bottle15-left-lower r0005`终端，不重跑。最多对三个新tuple发`9 Stage-A + 21 Stage-B = 30` planner queries；至少一个新survivor后，才把它与旧survivor一起进入最多4个physical candidates。至少两个physical pass才允许一次3-scene no-suffix diagnostic。这些中心性只是更有针对性的candidate依据，不声称IK/planner/physical已通过。Proposal SHA=`5203ca62afba5a594edabfd57ef0a0aa3e12106895ecf508478e4111f3451dd2`。

## F4：Guard schema预检

新增CPU-only `f4_guard_manifest_static_preflight_v1.py`，它在任何GPU操作前强制检查base Guard所有top-level/job fields、F4 asset map与文件hash、source/runner/Guard binding、全部资源上限、新output namespace及所有后续阶段为false。将历史Run13 manifest喂入该proposal-only预检时，会额外得到`proposal_not_authorized=false`，因为Run13本来就是`approved=true`的已消耗授权；这是预期的历史状态差异。与实际Guard `KeyError`直接对应的独立三项是：

- `all_guard_top_level_inputs_present=false`；
- `f4_asset_map_nonempty=false`；
- `all_f4_assets_exist_and_match=false`。

这与实际Run13 `KeyError: asset_hashes_by_family`一致。Validator SHA=`9b753daaa0d84da62a57e55ac241178147adc3c9cba09758c1eedeba598c3133`。下一步将在新source freeze后生成一份含完整asset map、`approved=false/executable=false`的F4提案清单，必须先让此预检pass，仍不代表允许第二次重开。

## 边界

三份工作都是CPU-only proposal/audit。未初始化GPU，未创建scene，未planner/physical/raw/video。Stage0重跑、Stage1、formal360、训练、H-reveal、compression、π0.5仍全部禁止。
