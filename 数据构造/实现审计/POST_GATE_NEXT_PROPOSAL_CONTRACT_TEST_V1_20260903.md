# Post-Gate next-proposal contract test V1

日期：2026-09-03  
状态：`PASS_CPU_4_OF_4`

测试文件：`tests/controlled_multi_future/test_post_gate_next_proposal_contracts_v1.py`  
SHA-256：`b177a7cf694ccc7835df4e8dddfd3d4a82a895951079eb18e6c34b3cea56d594`

覆盖：

1. F2精确`can0+box2/left/contact8/rotation0`候选、三program、75-query/8-scene/4-action/3-branch上限与`GPU/Stage1/formal=false`。
2. F3三个精确替换tuple及recipe SHA唯一性、已有survivor不重跑、30-query/6-scene/4-physical/3-no-suffix上限。
3. 历史Run13在proposal-only static preflight中必须失败：一项是预期的历史`approved=true`状态差异，另外三项是实际schema/asset缺项；新F4提案必须全14 checks和4 asset hashes通过。
4. F4提案显式execution rejection，以及统一review packet自哈希、GPU0–7范围和所有后续阶段为false。

首次运行为3/4 pass；唯一失败是测试曾把Run13的历史`approved=true`误当为本次schema根因集合之外的通过项。修正期望集合、明确区分历史状态与三个真实缺项后，第二次运行4/4 pass，24.094s。

全程未初始化GPU，未创建scene，未planner/physical/raw/video。
