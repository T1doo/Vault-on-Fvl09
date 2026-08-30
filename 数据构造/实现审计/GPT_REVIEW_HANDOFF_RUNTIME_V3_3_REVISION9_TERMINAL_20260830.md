# 给 GPT 的 revision-9 终止审阅交接

请直接审阅私有仓库 `https://github.com/T1doo/Vault-on-Fvl09` 的 `main` 最新HEAD。先完整阅读：

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`
3. `数据构造/实现审计/F2_F3_F4_RUNTIME_V3_3_REVISION9_TERMINAL_AND_REVIEW_STOP_20260830.md`
4. 同名JSON
5. 三份revision-9 evidence manifest
6. `数据构造/实现审计/REVISION9_GITHUB_SNAPSHOT_BOUNDARY_20260830.json`
7. `数据构造/实现审计/stage0_readiness_report_runtime_v3_3_cpu_current.*`
8. `数据构造/实现审计/f1_f4_implementation_registry_v3_3_cpu_current.*`
9. `数据构造/正式数据构造日志.md`第179–181节
10. `数据构造/实现审计/代码审阅快照/`

## 当前裁决

`BLOCKED_WITH_REASONS`，不批准Stage0。F1仍是唯一完整accepted nonformal root；正式轨迹为0。用户已要求Codex在revision-9后停下，等待你的方向审阅，不要把这份handoff理解为revision-10授权。

## 请重点独立判断

### 1. F2下一步应是延长settle，还是说明当前release/geometry仍错？

Revision-9 balanced-preload让开夹峰值从约`1.49m/s/14.78rad/s`降到`0.0166m/s/0.724rad/s`，且finger已物理脱离、box support连续，但50帧后仍`true_cavity_obb=false`且angular unstable。请检查partial trace、Gate时钟与box contact：

- 固定延长到250/更多帧是否是合理、非调参式的下一实验；
- 还是罐头已卡在盒边/侧壁，延长等待不会解决；
- balanced mean-aperture公式是否合理，是否需要更早/更慢/不同aperture；
- Gate要求full-OBB inside再full-open是否形成逻辑死锁。

### 2. F3是否应该停止研究release，先重做grasp robustness？

Revision-9 staged release三条都未执行。三条在原pre-open Gate前已出现`51–128mrad` bottle orientation error和`52–134mrad` grasp orientation drift；第一suffix event就出现约`53–57mrad`瓶姿态漂移，尽管contact fraction=1、break=0、EEF tracking正常。请判断：

- 这是否证明主要问题是瓶子在夹爪内滑移/抓姿不稳，而不是release；
- revision-8同seed能跑到release、revision-9却全部pre-open失败，说明哪些determinism/physics/contact问题；
- 是否应修改抓姿、夹紧方式、事件幅度/速度，或只改diagnostic tolerance；
- 哪些改变只是implementation repair，哪些需要physics/layout impact review；
- 是否应保留当前bottle与program，还是已达到family infeasibility证据。

请不要为了跑通而直接放宽冻结verifier。

### 3. F4的A_carry_mid IK应如何处理？

JSON问题已真实修复。A pregrasp/grasp/lift均planner success，carry-mid goal约`x=.155,y=.078,z=.9994`时IK_FAIL；0 execution。请审查：

- top-down grasp相对变换和carry-mid orientation是否把右臂推到不良工作区；
- midpoint是否应分成多个chained waypoint或先回已证明neutral carry；
- 降低由障碍物算出的carry height是否合理；
- 是否需要移动slot/tray/layout，以及若移动需要什么impact review；
- staged A是否应先单独执行到lift，再依据actual qpos规划carry，而非当前全链preflight。

### 4. 总体工程策略

Codex已做9个source-distinct revisions，基础pipeline/cleanup/raw/hash/authorization比较完整，但family物理任务仍未完整跑通。请判断当前是否过度局部修补，并给出下一轮更高层、有限预算的执行方案。最好明确：

- 哪些代码保留；
- 哪些机制应删除/简化；
- 每family下一版唯一假设与停止线；
- 是否应该先做更小的diagnostic micro probes再跑完整root；
- 哪些变化需要用户批准或科学版本升级；
- 什么证据才足以批准Stage0。

## Claim boundary

当前只能声称：F1 root accepted；F2 on/beside accepted且balanced preload显著降低release冲击；F3 V/H基础能力历史上成立但revision-9暴露grasp robustness；F4 A top-down micro历史通过且JSON修复成立。不能声称F2/F3/F4完整可行、Stage0 ready、H-reveal、compression或policy transfer。

请输出一个清晰的`BLOCKED_WITH_REASONS`审阅裁决、F2/F3/F4根因优先级、下一版有限工作包，以及明确哪些操作需要用户批准。Codex将在用户转发你的审阅后再继续。
