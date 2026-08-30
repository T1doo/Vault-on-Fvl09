# Stage 0 readiness：runtime-v3_3 revision-9 CPU current

## BLOCKED_WITH_REASONS

Revision-8 terminal evidence已发布；F1仍是唯一accepted root。Revision-9 CPU修复完成：F2为单一balanced-preload inside release，F3为单一symmetric staged release并修正diagnosis优先级，F4只修ndarray JSON canonicalization；raw新增明确语义的drive audit字段。

Active与byte-equal snapshot各427/427通过、diff零。下一步先发布clean revision-9 CPU baseline，再签三个single-use bundles；任何GPU run仍为nonformal、formal/stage0=false。Stage0继续禁止。
