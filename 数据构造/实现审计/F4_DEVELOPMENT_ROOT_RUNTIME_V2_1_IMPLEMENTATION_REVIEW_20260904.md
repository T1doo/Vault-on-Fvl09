# F4 development-root Runtime V2.1 CPU final-hardening review

日期：2026-09-04

状态：`CPU_FINAL_HARDENING_IMPLEMENTED_AND_TESTED_AWAITING_NEW_EXTERNAL_REVIEW`

本轮只新建 Runtime V2.1 和纯 CPU 测试证据。没有修改 hash-bound Runtime V2，
没有修改 F4 candidate、ABC/ACB/BAC、layout、arm schedule、planner terminal、机器人
动作、threshold 或 verifier，也没有签发 `approved=true` manifest。

## Runtime V2.1 冻结文件

- `f4_development_root_runtime_v2_1/manifest_contract.py`：
  `eb6afbb96d4737946dd8de8d527fc41afee98fac762fb3a1255ba877c5a06b4f`
- `f4_development_root_runtime_v2_1/guarded_launcher.py`：
  `1dd8188da117876b4b452b8dc96d5b35cf8d49d0daff190ed5eac9ffb9bb5454`
- `f4_development_root_runtime_v2_1/job_runner.py`：
  `7b47e1a7e3ad9fd0db528e23ee9d870029d527c5b2f47a3550fc545d3a257463`
- `f4_development_root_runtime_v2_1/lifecycle_preflight.py`：
  `fcb125438d19f71ff9a31ad353b7481935290c0f36a64e0e1427225369c5f0a1`

原 Runtime V2 四个文件的 SHA-256 仍分别为
`64484a94... / 884ccd6c... / e9217b43... / cc3c1db3...`，未被覆盖或改写。

## 权限与来源强绑定

新 contract 真实读取并绑定：

1. 最新外审正文 file SHA=`790fc6e3...`，以及 extraction/decision receipt
   `c8ff6925...`；
2. source proposal V1 file SHA=`227cb378...`、manifest=`8afaf49a...`；
3. Runtime V2 CPU review file SHA=`0a249108...`、receipt=`27685393...`；
4. Runtime V2 lifecycle file SHA=`33f2bc3f...`、receipt=`3df1f4c2...`；
5. 未来 proposal/approved manifest 必须再绑定本轮 V2.1 hardening test 的
   path、file SHA 和 receipt SHA；
6. 未来真实 approved manifest 还必须绑定新的 root-execution approval 正文和
   extraction receipt，且正文包含精确批准 token。CPU fixture 不获得真实批准能力。

Contract、Guard、runner 和 lifecycle 都以 manifest-bound 路径和 SHA 校验可执行
身份；contract 还将自身 `__file__` 与 manifest 精确交叉比对。

## RUNNER_ENTRY 加固

Runner entry 现强制：

- start receipt schema、`family=F4`、run/job/manifest 完全一致；
- physical GPU index 与 UUID 在 start receipt、`CUDA_VISIBLE_DEVICES` 和
  `CMF_GPU_GUARD_PHYSICAL_INDEX` 间一致，且只允许一个 UUID；
- start receipt lease path 与 `CMF_GPU_LEASE_PATH` 一致且文件存在；
- `CUDA_HOME=/nfs_share/lijunhui/Robotwin2/tools/cuda-12.1`；
- `PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin`；
- `PYTHONDONTWRITEBYTECODE=1`；
- 九个 cache 环境变量逐一指向 Guard 创建的九个对应目录；
- `LD_LIBRARY_PATH` 在 child environment 中完全不存在。

## 独立磁盘 finalizer

Runner 不再只相信内存 result 或 branch 中的布尔字段。它重新读取并比较：

- `development_root/root_receipt.json`；
- ABC、ACB、BAC 三个 branch `receipt.json`；
- 三个 raw 目录，并实际调用 `verify_raw_artifact_integrity(...)`；
- 磁盘 raw manifest 的完整payload、NPZ hash、manifest file hash与 sidecar
  hash 必须再与独立 branch receipt 中的 `raw_manifest` 精确交叉绑定；
- 三个 MP4 和 receipt，并实际调用
  `validate_development_trajectory_mp4_receipt_v1(...)`；
- root 与内存结果中的 branch receipts 必须都是恰好三个mapping，且以
  `F4-ABC/F4-ACB/F4-BAC` 顺序唯一出现；task-feasibility receipts 也必须
  是同一精确program顺序且全部passed；
- 三个 suffix receipt 的精确程序顺序、`planner_solvable=true`、42 个 query
  receipts、30 个 chain segment，从而独立得到 `12+30=42`，aggregate=126；
- 11 个非空且唯一的 `scene_instance_id`，以及精确 phase multiset
  `pristine=1 / task-feasibility=3 / canonical-prefix=1 /
  suffix-preflight=3 / strict-prefix-branch=3`；
- branch execution planner delta=0、final-state equivalence、same-current/anchor/
  prefix、9 个 role checks、10+126=136 和 cleanup/orphan evidence。

只有所有检查同时为真，finalizer 才产生 `accepted=true` 和 accepted counts `1/3`。

## POST_CHILD 加固

POST_CHILD 从磁盘重读并验证 Guard terminal、job terminal 和 root finalizer 的
self-hash及 run/job/family/manifest 绑定。它还要求：

```text
child_exit_code == 0
⇔ job_terminal.pass == true
⇔ root_finalizer.accepted == true
```

并交叉检查 Guard/job GPU identity、finalizer checks/failure、result 和 terminal 的
accepted `1/3`、formal=0，以及 Guard cache removal、lease release、task-owned cleanup
和 GPU baseline。一致的科学失败可被认定为“终端证据完整”，但绝不会被认定为 job
success，Guard 也不会返回成功。

## 机器测试

机器 receipt：`F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_FINALIZER_TEST_V1.json`

- receipt SHA=`1c546ace3994e5d2afb46f7490b6d0d3e55d9b666cb41e9cc54658bbe4b723f2`
- file SHA=`88c9b4d94158d724dc520898d0ee48196851e86fcaac18ad986725183a7ab6f1`
- overall=`pass=true`
- finalizer=`18/18`：1 个 accepted 3/3 正例和 17 个 fail-closed/serialization
  相关用例；
- runner environment=`21/21` negative rejected；
- lineage=`5/5` negative rejected；
- executable identity=`3/3` negative rejected；
- POST_CHILD=`1 success + 9 negative rejected + 1 consistent-failure correctly
  classified`；
- nested NumPy bool/int/float/array JSON serialization pass；
- temporary paths cleanup pass。

独立cross-audit在初版收据之后构造出四个会被错误接受的结构化负例：
协调替换NPZ+manifest+sidecar、额外null branch、branch倒序和重复的
task-feasibility program ID。本次最小补丁后，四个负例均由真实finalizer
fail-closed拒绝，并已纳入上述18/18机器收据。

测试使用 `require_execution_authorized=true` 的显式 synthetic fixture，走真实
PREPUBLICATION、GUARD_ENTRY、RUNNER_ENTRY loader 和 runner subprocess，但没有调用
真实 Guard main；临时 lease 只是未加锁 marker。机器 receipt 明确记录
`real_gpu_lease_acquired=false / nvidia_smi_called=false / GPU=false / scene=false /
planner=false / production_output=false / authorization_consumed=false`。

两次前置失败保留为实施事实：第一次 fixture child 缺少 workspace
`GIT_CONFIG_GLOBAL`，使 hash-bound git source audit exit 128；补精确 workspace Git
config 后通过。第二次 POST_CHILD synthetic terminal 写向重定向前的 fixture output，
被 contract 正确拒绝；改为从当前 job output 派生后通过。两次均在临时目录、无 GPU、
无 scene、无 real output，且 finally 完整清理。

## 尚存边界

- synthetic MP4 用于验证现成 validator 的 path/hash/bytes/frame/endpoints 合同，
  不代表真实视频内容；未来真实 root 仍由同一 validator 对真实 MP4 重验。
- 本轮只证明 CPU contract/finalizer/post-child 实现与负例行为；不证明真实 F4 root
  已执行或 accepted。
- 下一步只能由主线程生成 `approved=false/GPU=false/physical=false` proposal V2，
  运行 exact proposal CPU validation，并交新的外审。未经新批准不得启动 F4 GPU。
