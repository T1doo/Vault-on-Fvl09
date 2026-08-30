# Stage 0 readiness：runtime-v3_3 revision-8 CPU current

## BLOCKED_WITH_REASONS

Revision-8 active/snapshot各412/412、byte-equal且P0审计通过，但尚未真实运行。F1仍是唯一accepted root；F4 A-only micro已通过但完整staged/full仍pending。

下一步只允许F2-r8完整root、F3-r8完整root和F4-r8 block-root。F3首先验证真实SAPIEN shape identity/separation是否可用；任何缺失fail closed。F4必须按staged A/B/C/AB全部通过后才进入ABC/ACB/BAC。Stage0继续禁止。
