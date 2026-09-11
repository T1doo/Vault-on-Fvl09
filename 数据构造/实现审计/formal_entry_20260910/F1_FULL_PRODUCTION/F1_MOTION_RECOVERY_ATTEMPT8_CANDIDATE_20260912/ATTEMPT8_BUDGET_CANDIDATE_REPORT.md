# F1_000013 attempt8 候选（等待预算批准）

red 的 raw 已由修正后的 verifier 独立通过，并由 branch-local immutable overlay 绑定；旧失败 receipt/raw 不修改。attempt8 只计划复用 red，真实执行 green/blue。

- prior consumed: fresh/action/collection/solver/GPU = `18/9/1/0/1699`
- candidate total cap: fresh/action/collection/solver/GPU = `28/15/3/64/7200`
- candidate reservation: fresh/action/collection/solver/GPU = `10/6/2/64/5501`
- execution authorized: `false`; auto start: `false`

CPU preflight已通过：6条保留cell、red posthoc overlay、793步prefix和3个baseline来源均通过；preflight sha=`b2fb0c9de251737cb5e0a32644352eb7e08a67e9131712627a0780725a12b96c`。
