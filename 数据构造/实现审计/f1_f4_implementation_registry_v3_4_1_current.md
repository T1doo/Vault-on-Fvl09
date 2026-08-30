# F1–F4 implementation registry — runtime-v3_4_1 CPU current

| Family | 已完成的 CPU/code 修复 | 下一次非正式 Gate | 当前状态 |
| --- | --- | --- | --- |
| F1 | 4 target-construction + 11 control-chain 分账，三分支公用root runner | red/green/blue shared regression | **3/3 accepted, regression passed** |
| F2 | PreloadEntryEvidenceV11；v10 safety/final 源文件不变；primary/cleanup回执传播 | inside targeted | **Entry/Safety pass, final true-cavity fail; terminal** |
| F3 | canonical F3-* IDs，3 fresh contexts，shared-V + first suffix，no release/nonroot finalizer | three-context targeted | **canonical-prefix pre-V physical Gate fail; terminal** |
| F4 | exact variable-length segments/hash、per-segment joint evidence、fixed c1→c4、A-only、B/C planner-only | exact corridor selection + A | **fresh-scene candidate hash infra fail before corridor query; terminal** |

Source=`81c8603699c2fa086f524cb313e17aca205f00a575e7cc92588de6576c120ffc`；active tests=`461/461`。F1 regression不新增accepted root；历史 F1 accepted root 仍保留，accepted count 仍是1/4。后续运行必须等physical GPU0独立空闲，不允许GPU1–7。
