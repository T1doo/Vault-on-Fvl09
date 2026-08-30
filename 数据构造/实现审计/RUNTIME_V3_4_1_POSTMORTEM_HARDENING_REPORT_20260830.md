# runtime-v3_4_1 one-shot postmortem hardening 终端报告

## 总体裁决

**BLOCKED_WITH_REASONS**

CPU/source hardening 真实完成，但四个family targeted Gate只有F1通过。F2/F3/F4都按one-shot停止，所以没有签发任何conditional full-root authorization，也不生成Stage0 approval request。

## CPU/source 闭包

- design=`controlled_multi_future_f1_f4_v1_2`
- implementation=`controlled_multi_future_runtime_v3_4_1`
- source SHA=`81c8603699c2fa086f524cb313e17aca205f00a575e7cc92588de6576c120ffc`
- active/snapshot tests=`461/461` each
- active/snapshot compile=`151/151` each
- byte-equal=true
- official tracked baseline=`c3ddfa8b97d5519efa828b075999bd0006778e5e`，tracked files unchanged
- 本版没有第二次source freeze，没有v3_4_2/revision retry

## Family 结果

| Family | 实际结果 | 计数 | 是否解锁 full root |
| --- | --- | ---: | --- |
| F1 | red/green/blue 3/3 accepted，root finalizer accepted，三条executed-prefix hash相同 | 46/3/0 | 不需要；这是历史F1 root的回归 |
| F2 | EntryV11 pass、ReleaseSafetyV10 pass、full-open +250帧pass，但FinalInsideV10的true-cavity/exclusive-inside fail | 22/1/0 | 否 |
| F3 | canonical IDs正确，但canonical prefix的pre-shared-V抓取/接触/离桌Gate fail，三context未执行 | 7/0/0 | 否 |
| F4 | pristine/prefix pass，但fresh candidate在第一次corridor query前的application hash不一致，fail closed | 10/0/0 | 否 |

## 关键claim boundary

- F1：可以说v3_4_1 shared harness回归完整通过，但不新增accepted root。
- F2：可以说Gate分责被真实测试，安全Gate允许全开；不能说inside task成功。
- F3：可以说D3 alias软件障碍已消除；不能说three-context diagnostic或完整F3通过。
- F4：不能说四条corridor不可行，因为0个corridor进入真正planner query；只能说fresh-scene candidate hash稳定性仍是基础设施blocker。

## GPU/安全

按fvl05最新规则只用physical GPU0，四个scope串行。每项precheck均P8/14MiB/0%/无compute，每项postcheck均回P8/14MiB/0%/无compute；全部source-lock pass、no timeout、orphan=0。

## 当前总状态

- accepted nonformal pre-Stage0 roots=`1/4`（仅历史F1，本轮increment=0）
- Stage0 trajectories=0
- Stage1 trajectories=0
- formal F1–F4 trajectories=0
- `H_reveal=null`
- training/compression/π0.5=未授权、未开始

因本v3_4_1是单次source freeze，不在本版内修正F2/F3/F4或自动运行新版。下一步必须是新的用户/外部审阅与impact decision，Stage0继续禁止。
