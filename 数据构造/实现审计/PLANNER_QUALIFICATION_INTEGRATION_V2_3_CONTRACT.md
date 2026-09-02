# Planner Qualification Integration V2.3 Contract

状态：CPU/source seal 已完成；真实 planner/GPU/physical execution 未授权。

- Frozen Vault commit：`0244ca807426dd67694878f074651a90e25821ca`
- Active/snapshot source tree：`b3c492656aaa8efdd00b64656bc8e3930d2fb29d7a9968afa3a8f64d602d1d1b`
- RoboTwin tracked HEAD：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- Manifest bundle：`d4f0ec11f15e0849e4da6ab0febd0028533f09d7637cef2c05ce497d9a9814a9`
- Contract payload：`91c0be67a0aeeb716c627b2f94b6a999ad359d82529b8d0ed4264231d919b74c`

Production runner 不接受任意 callback 注入。Issuer 必须逐 job 绑定 manifest、runner symbol、planner seed/reset receipt、唯一 scene/output/authorization、O_EXCL、source lock 和 GPU0–7 Guard；schema/infrastructure/Guard/cleanup 错误停止整波，真实 planner `Fail` 才作为候选 terminal evidence。

任何 source 变化都会使基于本 contract 的剩余 authorization 失效。本 contract 自身不是 authorization。
