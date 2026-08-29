# 用户授权：runtime-v3_3 revision-4 continued repairs

用户在当前线程明确允许在保留全部失败证据的前提下持续寻找原因并修正。Revision-3已安全失败并形成impact review，因此本文件将该授权落实为F2/F3/F4各一个source-distinct revision-4 slot：

- F2：同layout历史safe sector + center-aware support z；
- F3：保持r3物理动作不变，补齐structured pre-V evidence与partial trace；
- F4：A/B/C统一60° inward-tilted right-arm transform；
- 每family revision-4最多一次full-root invocation；
- GPU0–7任一independently fresh-idle卡可用，不同family可并行；
- automatic retry=false、recovery=0；
- Stage0/1/formal/training/compression/π0.5仍未授权；
- 不允许放宽verifier或修改F3/F4程序、同对象/arm、40/360、R=3、split。

```yaml
approved: true
maximum_new_implementation_revisions_per_family: 4
maximum_full_root_execution_per_revision: 1
allowed_physical_gpu_indices: [0,1,2,3,4,5,6,7]
parallel_independent_jobs: true
automatic_retry: false
recovery_attempts: 0
formal_stage0_authorized: false
formal_collection_authorized: false
training_authorized: false
```
