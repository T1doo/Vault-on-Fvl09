# S4严格出口设计；未实施/未生成输入/H视图

出口只允许明确typed五字段，不允许原raw字典任意嵌套对象穿透：

- current_rgb：三路固定相机的uint8 H×W×3数组，实际current component来源hash；禁止dict/path/未来RGB。审计hash留独立sidecar，不进tensor。
- current_robot_state：初始38qpos+38qvel的float64/既定后续representation，当前只定义来源/类型，未更改或拟合归一化。重复articulation别名必须先原lossless核验，不能当76关节。
- future_effective_setpoints：仅原26维250Hz有效设定值；完整字段来源独立固定，不将requested/planner_goals/masks/object/finalstate拼进去。本轮不切H、不导出样本。
- candidate_program_semantics：冻结候选结构的语义内容，必须有显式program schema字段列表和类型；不得携带selected candidate ID、local class ID、分支/路径/instance ID。候选全集与选中目标/索引严格分离，置换时语义集合和监督索引对应须在未来接口测试中验证。
- visible_referring_expressions：只按协议允许的可见指代表达；禁止normal answer-bearing instruction、调试标记、source path。

所有未知字段、错误数组dtype/shape、嵌套dict、对象标量均fail-closed；同义命名/列表内字典也不能绕过。不能以递归删除字段替代typed schema，更不能把正常候选语义的合法对象引用当作运行instance ID。
sidecar保留root/program/branch/planner/pose/contact/verifier/事件时间等审计真值，但类型必须与模型tensor包分离，不可任意merge。

待执行负例：顶层path/branch；current_rgb内嵌path；future tensor替换为含planner_goal的dict；candidate语义夹selected ID；normal instruction；future RGB；array object dtype；NaN；错38/76；候选顺序变更但监督索引未同步。预期逐一拒绝或schema级明确处理，false不能因非空dict变true。
本文件只有设计和反例清单；active model_view.py未改，没有模型/训练/H视图或实际export验证。
