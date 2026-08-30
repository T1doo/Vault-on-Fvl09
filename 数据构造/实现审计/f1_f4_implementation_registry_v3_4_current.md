# F1–F4 implementation registry：runtime-v3_4 current

| Family | 当前冻结实现 | 下一Gate | accepted root |
|---|---|---|---:|
| F1 | 历史accepted保留；v3_4 regression在planner count一致性失败 | external review；0 execution | 1 |
| F2 | 旧pre-release angular Gate先失败，新v10 safety Gate未到达 | impact review；不开放root | 0 |
| F3 | D3 alias在task-feasibility失败，0 planner/0 diagnostic execution | 审阅是否允许replacement | 0 |
| F4 | 四个carry-mid均pass，四个A_preplace均fail | layout impact review；不执行A/root | 0 |

Phase0 active/snapshot各`449/449`，source byte-equal=`1cadd3e2…b316`。GPU0/2/3/4并行审计安全通过，但四个targeted scopes均未通过；accepted roots仍`1/4`，Stage0未授权。
