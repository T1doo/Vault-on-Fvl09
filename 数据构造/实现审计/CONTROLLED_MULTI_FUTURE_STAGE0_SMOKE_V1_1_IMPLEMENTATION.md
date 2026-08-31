# controlled_multi_future_stage0_smoke_v1_1

状态：`CPU_READY_SINGLE_F4_V13_GATE_PENDING`。

本版本只修复F4 terminal neutral的provenance：pristine canonical prefix artifact冻结target pose；fresh reconstruction直接复用该immutable target，不再从post-prefix common-X或旧layout neutral重算。Target specification要求exact identity；真实prefix replay继续使用已有physical anchor/prefix-end tolerance。

保持不变：前七个F4 targets、layout、right arm、common-X程序、A/B/C-slot映射、release、ABC/ACB/BAC、verifier与v12 `1e-5m/rad`审计。V13在其上增加exact specification Gate，不放宽阈值。

每条真正生成的Stage 0 trajectory还必须生成独立head-camera MP4（25fps、250Hz每10步采样、initial/final frames）；无trajectory的失败明确标记不适用，不伪造视频。Raw/MP4 file hashes与receipt由family runner和finalizer重新验证。

CPU证据：active/snapshot各`512/512 passed`；180个source与92个test Python文件compile通过；active/snapshot byte-equal。Source SHA=`41a6ede4e2b4dea01e7587ead948358023aeae2972006c31fce076bb96b31063`，tests SHA=`3d809044eabd92de0ca4bf0b7293ac3bd2486092b7a8f763d058dbf732846473`，budget SHA=`8aab303dfdf0f33d9558b8e67fe8c59564d8881d73ccf96301a6f676ea72bf1a`。

下一步仅签发一个新的`F4_candidate_hash_infra_v13` single-use bundle。只有Gate证明binding/8 targets、physical replay和至少一个真实candidate corridor query都通过，才生成`STAGE0_SMOKE_ATTEMPT_MANIFEST_V1`并执行12次Stage 0。Stage 1/formal/training仍禁止。
