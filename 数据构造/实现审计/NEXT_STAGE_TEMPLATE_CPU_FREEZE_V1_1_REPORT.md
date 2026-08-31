# Next-stage template CPU freeze V1.1

V1.1修复F2 authorization的双self-hash循环，并把未消费的F1/F3/F4 run1 bundles封为`UNCONSUMED_SUPERSEDED_DO_NOT_RUN`。

- Active tests: `635/635`
- Review-snapshot tests: `635/635`
- Active/snapshot byte-equal: `true`
- Source SHA: `ed8c2c461dd42ca5559c31b09f6abc8b41cac9a85f113fa2ee44903a17c9997e`
- Tests SHA: `b84eb5abd02d195a3bbf8c45c90d1aa3749af1947a9b2f4faaa1e345dc1a0dd7`
- Authoritative authorization hash: `receipt_sha256` only
- New identities: F1/F3/F4=`run2`; F2=`run1`（此前未生成artifact）
- No authorization has been consumed and no GPU job/output has started.
- Stage 1、formal、training、H-reveal、compression与π0.5仍未授权。
