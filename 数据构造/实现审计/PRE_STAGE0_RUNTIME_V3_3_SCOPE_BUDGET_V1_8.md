# runtime-v3_3 pre-Stage-0 scope budget v1.8

Revision-9 source-bound envelopes保持F2=`32/3/0`、F3=`96/3/0`、F4 block-root=`118/7/0`；新增分段开夹只增加250 Hz controller steps，不增加planner query、root execution attempt或recovery。Outer limits/timeout仍分别为`96/4/7200`、`160/4/10800`、`256/10/20400`。

F2只允许一个balanced-preload partial-open→fail-closed inside/support/disengagement Gate→full-open假设。F3只允许一个balanced-preload→固定`+0.16` normalized slow-disengagement→fail-closed return/support/disengagement Gate→full-open假设。F4只修NumPy JSON canonicalization。Automatic retry=false、recovery=0，每family revision-9最多一个full-root scope。

按当前fvl05执行边界，只允许physical GPU0且必须启动前fresh-idle、独占、UUID绑定、完整cleanup/postcheck。Stage0未授权。

Budget receipt SHA-256：`56b5d18115e5c0f7d24738ab49909633f26a69fd8e4b2b6235952f1c4751687f`。
