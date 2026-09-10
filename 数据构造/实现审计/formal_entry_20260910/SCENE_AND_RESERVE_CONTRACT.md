# 场景、划分、cohort与reserve合同

`scene_plan.py`是实际纯CPU生成/校验入口，使用显式ValueError/type/range/finite检查，不依赖assert；修改一个slot不会改变其他slot或下一次generate。旧plan.py和旧raw保留。

40主root+16有序reserve。每族10主root，每根3×3；train/validation/test=5/2/3，交叉难度为train1/3/1、validation0/2/0、test1/1/1。未激活reserve只有planned slot，candidate/current/prefix hash为null；已解析40场景仍是provisional配置，不是完成物理资格后的candidate freeze。

## 真正消费的参数

| 族 | 固定资产/语义 | 实际配置与变化 | 消费入口 |
|---|---|---|---|
| F1 | 历史真实模板是.044m边长红绿蓝块，plasticbox model3；不是此前文字误写的罐 | 三identity按位置轮换，公共容器、两个相似干扰物和背景物；对象间距由head投影比求解 | native_f1_factory.create_roles/bind_cameras、F1 controller |
| F2 | 071_can model0原scale/碰撞底点；box/scale/stand；旁放support=table | 设施在x约-.30/-.06/.18三个位置区域循环分配，10root每设施4/3/3；实际role位姿、容积和目标区域列入spec；主体与两个同类干扰物/背景物明确 | compatible_spec、native_scenes、native_cells、独立F2几何门 |
| F3 | 114_bottle model1、原竖抓物性、pad；VVHH/VHVH/VHHV | 主瓶/pad/工作中心、两相似瓶/背景/marker全部显式；工作中心位置与“保持实际抓姿”策略分开，不声明未消费的EEF四元数；table±z/±x | native_f2f3/native_scenes/原事件与rest verifier |
| F4 | 原.044m块X/A/B/C，008_tray model0原旋转姿态，固定object-slot映射 | X、源对象、各slot、托盘、两干扰物逐role显式，三顺序一律重新新布局资格 | native_f4_qualification/native_f4/独立F4磁盘门 |

F2保持direct geometry route/.12m lift候选，不返回旧高位中转；box/scale/stand当前尺寸和高度冻结，篡改尺寸后重算hash也拒绝，防止scene/verifier分歧。F3 .047m对称事件，三个标签同样time scale1.5；motion用预声明event holds，F2用35/40帧保持，F1/F4用35帧post-prefix保持。严格P仅r_pc三格；inv可以自愿复用prefix，但不以全九格P相等定义成功。

每个spec包括角色、资产文件SHA、原物性来源、位姿、size、target、cameras、程序和变体。源资产缺失或更改拒绝；program不仅比ID，也比完整canonical步骤。所有新范围仅CPU构造、PHYSICS_PENDING，不称为原成功profile覆盖所有新布局。

## 难度与近重复

head固定K/E与320×240；以指定对象对的世界AABB投影中心横距/较大投影宽度计算。F1选择相邻active对，F2 main_can/similar_1，F3 bottle/similar_1，F4 A/B；二分解实际x坐标达到clear2.2、medium1.75、crowded1.35。逐role投影bbox输出在spec。它是几何预检，不证明渲染遮挡、足够像素或全机械臂抓取净空；这些仍在真实资格/采集门核验。

物理signature只取真实角色geometry/asset内容/color/material和相机数值，不取rootID、seed、注释或无效appearance字段。跨split近重复比较任务对象/设施，排除背景和干扰物对判定的“掩护”；同类配置全部任务role位置差≤35mm则判近重复。train整体x0–8mm/y0，validation x约-45mm/y+25mm，test x约+45mm/y-25mm，任务布局本身不同。近重复在同split保留相关lineage，不宣称统计独立/强泛化；阈值于物理采集前冻结，不根据成功率改。

## 确定性reserve

`activate_reserves`有NFS锁和持久化barrier。先等冻结首波rank1–2全部terminal，再按原primary rank分配reserve；后续rank3–10必须等首波及其replacement链关闭。worker完成先后不影响映射。重启同一barrier幂等，旧失败/activation保留，rank不重复。reserve原seed/rank/inherit字段不改，另生成继承split/difficulty的resolved spec和所在split的真实位置范围；reserve失败可继续使用下一个rank。耗尽则数据集incomplete，不偷偷加slot。

## 调度附录（集中待确认）

先冻结全部56slot/generator/split/规则，再逐族满足同等数据资格并采该族。与canonical“先全40 active candidate冻结再Stage3”相比，只改变执行调度顺序；需首波授权一并确认。数据门不依赖模型准确率或H-reveal，科学实验门原定义保留；不启动训练/压缩/高清来充当采集前置。
