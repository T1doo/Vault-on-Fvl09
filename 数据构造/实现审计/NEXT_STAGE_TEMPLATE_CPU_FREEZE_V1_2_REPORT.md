# Next-stage template CPU freeze V1.2

V1.2统一F2 canonical与execution-layer的absolute output namespace，并新增完整canonical authorization构造测试，避免再次逐字段签发失败。

- Active tests: `636/636`
- Review-snapshot tests: `636/636`
- Active/snapshot byte-equal: `true`
- Source SHA: `f926be2048dff9a521f3cab9e6f7e1dfdf09b69e54baf2fd162322061299db8a`
- Tests SHA: `da9183010c24516b57f607cc58a41b0ebe2b032f35e8bd66c9a3cde61b2c535b`
- F2 full canonical authorization construction: pass
- Basename output tamper: rejected
- F1/F3/F4 next identities: run3; F2: never-written run1
- No authorization consumed, no Guard/output/GPU job started.
- Stage 1、formal、training、H-reveal、compression与π0.5仍未授权。
