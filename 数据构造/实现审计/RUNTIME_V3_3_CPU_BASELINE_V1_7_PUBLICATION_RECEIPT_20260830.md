# runtime-v3_3 CPU baseline v1.7 publication receipt

```yaml
content_commit: e232ed7b3cf66ee20eaa910652b85cfb915b40ce
branch: main
origin_main_match: true
implementation_source_sha256: adc93d707fb2e2fde01b2915f160d769746ea148465f6772b7f4143a02453cb9
budget_receipt_sha256: 7039690e7ceeaf5edbf9c66f853bb116a8757218dd0039795eb8dc12e1f2f8f3
active_tests: 287/287
snapshot_tests: 287/287
source_and_tests_byte_equal: true
formal_data: false
stage0_data: false
stage0_authorized: false
```

本发布封存 F2/F3/F4 revision-2 失败证据、revision-3 implementation-impact修复、budget/parent authorization v1.2、current registry/readiness和byte-equal代码审阅快照。发布时未运行revision-3 GPU，也未生成Stage 0数据。

不可变r2 namespace trees：F2=`8e735bb894c1da4a2825933097a60350c603962bdd27b8e24a6223bae900203e`，F3=`9d6e711f5f02fe9372cfb4d14e495bff74d20e6d38bff3b51643d9fdbb74dced`，F4=`effc52ce16925787710652b77a54ee7671718b7df6bb4db6078614cc92230ebf`。

下一步仅允许在本receipt closeout也发布、Vault恢复clean published HEAD后，为F2/F3/F4 revision-3分别创建全新single-use request/source-lock/authorization/guard/output namespace。

