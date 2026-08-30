# Stage 0 readiness：runtime-v3_3 revision-8 terminal current

## BLOCKED_WITH_REASONS

Revision-8 三个非正式 GPU scope 已真实终止并完成 cleanup/source/GPU 审计。F1 仍是唯一 accepted root；F2 为 `inside fail / on pass / beside pass`，F3 为 `1/3 accepted`，F4 在 A preflight 因 ndarray JSON 序列化缺陷以 0 execution 停止。

下一步先发布 immutable revision-8 证据，再做 source-distinct revision-9 CPU 修复：F2 单一 staged release、F3 post-release roll impact review 与 diagnosis Gate 修正、F4 JSON-safe canonicalization。任何新 GPU scope 都必须使用新 source/hash/budget/namespace/one-shot authorization。Stage0继续禁止。
