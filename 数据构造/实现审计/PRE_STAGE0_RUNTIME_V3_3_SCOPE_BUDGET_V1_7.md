# runtime-v3_3 pre-Stage-0 scope budget v1.7

Revision-8 exact source-bound envelopes：F2=`32/3/0`，F3=`96/3/0`，F4 block-root=`118/7/0`；outer limits/timeout分别保持`96/4/7200`、`160/4/10800`、`256/10/20400`。

F4的118/7严格由`10 common prefix + staged A/B/C/AB各7/query + 10 full-root prefix + ABC/ACB/BAC共9 blocks×7`组成。任何staged failure停止full root。Automatic retry=false、recovery=0；Stage0未授权。

Budget receipt SHA-256：`bd62453d41b214a54eea045a9b9d6f641c8802cf2f384143a9e7b71d7e61b14a`。
