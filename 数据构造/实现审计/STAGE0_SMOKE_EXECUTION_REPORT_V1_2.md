# Stage 0 smoke v1.2 — replacement-aware terminal report

## 最终状态

```text
STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE
```

Stage 0 attempt phase与canonical seal现在均已完成。Active denominator仍为12个slots；历史共15份terminal attempt receipts（原12 + F2 replacement 3）。正式数据仍为0。

| Family | Active结果 | Raw / MP4 | 结论 |
|---|---:|---:|---|
| F1 | 3/3 PASSED | 3 / 3 | Stage 1 candidate-ready |
| F2 | inside failed execution；on/beside PASSED | 2 / 2 | scene-layout wiring已修，真实物理结果有效 |
| F3 | 3×FAILED_EXECUTION | 0 / 0 | shared pre-V physical failure，进入post-Stage-0 impact review |
| F4 | 3×FAILED_PLANNER | 0 / 0 | v13旧layout无可解corridor，进入layout impact review |

Active总计=`5 success / 7 failure / 5 raw / 5 required MP4`。所有generated trajectories都有可验证MP4；无trajectory slots不要求伪造视频。

## F2 replacement

F2 run2在physical GPU4完成，预算=`32 planner / 3 execution / 0 recovery`：

- frozen layout/current/anchor与历史intended layout reference逐字段、RGB hash和pose一致；
- 原v1.1 missing-layout default current明确不比较；
- inside被原`F2ReleaseSafetyGateV10`在full-open前阻止；
- on与beside动作、verifier、raw、MP4全部完成；
- on/beside MP4分别302/370帧、25fps、320×240，首尾帧均实际解码成功；
- 11个scene均cleanup安全，orphan=0；GPU4 post=`12MiB/0%/P8/no process`。

Run2 raw最初因`family_runners_v3_3._raw_result`未映射adapter v1.8而误写implementation label=`runtime_v3_3`。两个raw除该label外的完整性、realization binding、verifier v1.2、source lock、MP4均通过。通过不可变provenance correction overlay修正解释；原raw/manifest/branch receipt/video未改字节，也未重跑物理attempt。

## Authoritative seal

```text
result payload SHA = 394093a2571269eaa659cc90df654c449ffd1fb3a9ab041bbcfc321231c21df7
result file SHA    = 228c9a425f88105472b3dff0e767431d10d306a4271fa575ec789cc6ef8c7c42
seal SHA           = 08ef2c20e6508b32a026fcd168ce5b69bb8686cec0071e5a243d7e211e810783
```

Stage 0封存完成不等于四个family已可稳定扩量。Stage 1仍未授权；F2 inside、F3 prefix和F4 layout仍是pre-Stage-1开发问题。
