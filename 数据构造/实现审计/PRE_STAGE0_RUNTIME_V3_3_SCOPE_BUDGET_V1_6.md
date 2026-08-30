# runtime-v3_3 pre-Stage-0 scope budget v1.6

Revision-7 exact scopes保持原source-bound planner/execution envelope：F2=`32/3/0`，F3=`96/3/0`，F4 micro=`13/1/0`；outer limits与timeout分别保持`96/4/7200`、`160/4/10800`、`16/1/7200`。

本budget只批准single-use nonformal revision-7 repairs，automatic retry=false、recovery=0；用户允许后续继续source-distinct修复不等于同一revision无限重试，也不授权Stage0。

Budget receipt SHA-256：`1a3e2e18acc8af984dbb76e637ac140c930c332748202e7b61564b77c86f8d62`。
