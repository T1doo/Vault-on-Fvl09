# 四族批量方案（草案、待执行授权）

40个新主root、16有序reserve；每族10×3意图×3真实realizations=90条，总360。旧pilot不占360且不进untouched validation/test。每root固定执行臂/调度和250Hz；pc/path/motion均真实执行，不能拼接A/B或对保存raw重采样充数。

## 参数与范围

下列数值都是拟用范围，除明确历史锚点外均“首波待验证”。`PLANNED_SLOTS.json`只冻结草案槽位，物理观测hash全null。毫米级平移只是首波低风险变化，不足以证明正式多样性；最终还须投影难度、identity轮换和跨split近重复检查。

| 族/参数（单位） | 首波及依据 | 主批候选/联动约束 | 消费处与失败处理 |
|---|---|---|---|
| F1 active中心(m) | 历史x=-.20,-.11,-.02,y=.02,z=.762，加整体dx=.002/.004、dy=-.001/0 | 三中心以-.11为簇中心；三identity按3循环轮换，左右出现3/3/4，候选展示顺序另行置换 | `_layout`→scene_layout→factory→grasp；实际布局不同才算新root |
| F1间距/容器(m) | 历史9cm中心距、box[-.08,-.16,.78]是控制参考 | 拟中心距{.075,.090,.105}，容器与簇整体平移；同root三分支完全一致；先用实际相机投影验证clear/medium/crowded，不从cm直接赋难度 | 抓取包络不得互推；投影宽距目标分别2.2/1.75/1.35，达不到则slot资格失败 |
| F1资产/属性 | 沿成功三近邻同类罐和容器，size=1、原物性 | 颜色/identity轮换，两个相似干扰物、一个背景物按规范；换实例、尺寸、纹理首批不启用 | common-prefix必须在选择具体对象之前结束；visibility检查不使用标签位置捷径 |
| F2主罐/设施(m) | v5 A：box[-.24,-.18,.755]；stand[.14,-.06,.79]；scale按保存spec；拟group dx=.002/.004 | 主罐初态、所有设施和合法目标同步平移；10root拟dx=.002至.020、dy∈{-.001,0,.001}；reserve至.028 | `scene_spec`→F2 factory→target几何→independent verifier；不能仅换seed |
| F2运输/支撑(m) | side_then_geometry_target；A .16 lift/B .12 lift分别保留 | 首波选B .12 profile作资格候选；40mm path绕行及既有motion holds对三标签一致；inside容积、scale顶面、stand旁环带+table支撑互斥 | 取消旧高位side_at_target；不改成功门，失败保留/按reserve处理 |
| F2几何/尺寸 | 071_can model0及实际collision底点，尺寸固定 | box壁顶.855、底面由构造推导；旁放reference=stand/support=table；其他设施尺寸不变 | 目标生成与验收分离；尺寸扩展必须联动净开度/退出/支撑，延期 |
| F3 bottle/pad(m) | P3 A瓶[-.18,-.06,.750]、pad z=.745；B x=-.14 | 同步平移瓶/pad：拟dx=.002至.020、dy±.001；工作中心随group移动；原资产物性和竖抓固定 | `scene.py`消费显式spec，不借默认A/B；新场景净空资格未测 |
| F3工作高度/事件(m,s) | 指令振幅.047；B已成功time_scale=1.5；rest执行前冻结 | z_center ≥ 台面/设施最高点 + 实际夹持总成向下包络 + 负V振幅 + .010净空（.010为拟用）；table ±z/±x不变 | `_closed_loop_event`/独立事件门；同root所有program用相同速度profile；3cm path绕行、motion时长规则均按realization而非标签 |
| F3干扰/可见性 | 同类干扰瓶2、普通干扰物1–2按规范补齐 | 固定资产，位置离夹持包络≥.020m（拟用）；目标必须可见；投影难度按D4检查 | 角色增加不得被当前固定role列表漏验；不改变V/H及rest |
| F4源/slot/common(m) | 原qualified mixed-arm source和slot映射作基线 | 所有源物、对应slot、X托盘按group dx=.002至.020/dy±.001联动；不独立随机slot；尺寸/朝向冻结 | qualified-root adapter→full_program_specs→plan/execute；每个顺序重新资格 |
| F4拥挤/变体 | 使用原成功path/motion profile | 保留A→slotA等固定映射；path仅改轨迹，motion仅改保序节奏；干扰物1–2不制造自然先决顺序 | 三程序均可行；whole-world terminal/neutral/非任务物完整验证 |

主批拟用数值不是所有40root的实测安全范围。generator须以保存的asset尺寸/相机投影计算间距和可见性；若上述小范围不能满足难度/角色规范，记录计划冲突，有限reserve仍不满足就停止该族，不能事后改难度或凑数。颜色轮换是F1/F4语义外观设计；F2/F3不从无意义appearance字段声称多样性。

## Split、reserve和首波

每族train=5、validation=2、test=3；train难度1 clear/3 medium/1 crowded，validation=2 medium，test=1/1/1，总2/6/2。所有同root/super-root及派生view同split。slot 1/2为train clear/medium，首波每族2完整root共18条，属于该族90条。其余8主root=72条；每族reserve rank1–4按失败槽继承split/difficulty，禁止提前生成current/candidate/prefix hash。

未来执行严格F1→F2→F3→F4，同族最多8张当时fresh-idle卡、一root一卡；首波最多2卡。先完成4族CPU计划；不同族物理不混跑。copy默认一个I/O worker，首波测吞吐后至多2个。

首波放量门：两个新root均9/9独立通过；实际current/anchor/prefix及candidate完整；两root参数与实测current不同且无跨split近重复；真实输入磁盘导出、原文件hash、独立副本读回通过；共享代码错误0、未知消费0、自有worker残留0；每root solver≤240/360/480/900（F1/2/3/4）、lease≤3600/3600/4500/9000s。任何普通不可行可按rank用reserve替换，原失败计入分母；每cell最多一次基础设施修复后的重试，各族共9额外cell封顶，不为物理不可能反复换seed。两个首波完整root通过仅放行该族剩余冻结任务，不宣称可靠总体成功率。

家族关闭的机器条件：10个accepted root×9唯一cell；所有源/hash/current/语义/前缀/变体/终态门通过；split×difficulty配额满足；manifest无重复；reserve activation可追溯；copy终端全部通过；budget reserved=0且无unknown/overrun；owned cleanup全通过。未满足不进下一族。外部任务后占卡不反判自身cleanup失败。

## 数据生产门与科学实验门

数据门：三程序可行→freeze candidate/task tree/prefix→完整采集→独立验收/去重/归档；模型不参与成功判断。科学门：future-content、Temporal Identifiability、H/P、K、policy按原顺序，均后续独立授权。canonical D17 Stage2要求40个candidate冻结后才整体Stage3，与用户逐族首波即正式采集存在执行顺序差异：提案为逐族完成同等Stage2数据前置再Stage3，保留全体slot/split/阈值事前冻结；需一次批准该调度解释，不能静默删掉科学定义。
