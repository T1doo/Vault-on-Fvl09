# 统一状态：真实微门与有限路线比较已结束

Development accepted仍6 roots/18 trajectories（F1 5/15，F4 1/3）。F4已接收，不重跑。

F3本次28queries/8scenes/2physical，pregrasp2/2通过、grasp0/2、闭爪0；转同一证据的planner/physics模型一致性修复。F2本次6queries/2scenes，D0通过、U/D和三条route均IK失败，转固定目标/抓持变换约束审查。两任务都清理完整，授权已消费，无自动retry。

隔离公共CPU实现通过26tests，包含原collector隔离副本的完整发布流程；有12个F1/F4 realization操作提案、48个Stage1 cells及40+16个pending schemas。具体family绑定仍需收口，未宣称新物理采集完成。

Stage1按root A/B各6条，总48；formal才要求每root9/9。9个cells是候选复用，不是已接收数据；Stage1仍0/48、formal0/360且未授权。

详见同名JSON和唯一总交接GPT_HANDOFF_F3_MICRO_F2_TRANSIT_DOWNSTREAM_20260905.md。
