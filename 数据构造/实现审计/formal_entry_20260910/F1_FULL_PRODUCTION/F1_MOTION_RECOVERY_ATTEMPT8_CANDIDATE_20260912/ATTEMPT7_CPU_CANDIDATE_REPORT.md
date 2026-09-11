# F1_000013 attempt7 CPU candidate（未授权）

该目录只封存 attempt7 的候选绑定，不代表物理授权，也没有修改 attempt6 runtime STATE、ledger、output 或旧回执。

- checkpoint old implementation: `574a205b0b0fa0afebacbc2c4a2369e1cf3afaf50474ade085fb25be7943357e`
- checkpoint old source bundle: `2307946b4beb99492fc5f7fc8c1464841bcd9df593fd393f15517f07d9e885bc`
- candidate implementation: `c8dcac07a69557f7ca0e99b88619232bb2b693fdb9d6419904cd67bc75abbca2`
- candidate source bundle: `c8c3e10c4d8816150c0c0140c1136fd784cb59cba7fdcb1aa06f1fe16c98910b`
- candidate contract: `6588e52b54c1b8061bb5fea9bf7d16b895fb5e4cceb9c03a80edc06ac4bf4cdd`
- previous attempts: 6；最后一次在场景创建前退出
- prior consumed: fresh/action/collection/solver/GPU = `9/4/0/0/649`
- candidate reservation: fresh/action/collection/solver/GPU = `11/7/3/64/6551`
- missing cells: `F1-red/green/blue:r_inv_motion`
- fixed GPU UUID: `GPU-2c620e6c-9639-2022-b573-9847dfa33769`
- execution authorized: `false`
- auto start: `false`

本候选修正了 attempt6 暴露的接口问题：compatibility 的旧实现身份以 root checkpoint 的 `574a...` 为准，而不是沿用未进入 root 的 authorization candidate `c8dc...`；新的 source bundle 则绑定当前代码。实际 output 中的旧 compatibility 回执没有替换，因此不能把本候选直接当成已完成的 preflight。物理续跑前仍需一次新的明确授权、独立 STATE/ledger contract amendment，以及真实 `recovery_cpu_preflight`。
