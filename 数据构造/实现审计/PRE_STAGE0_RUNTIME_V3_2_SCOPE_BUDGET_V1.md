# Pre-Stage0 runtime-v3_2 scope budget v1

```yaml
schema_version: cmf_runtime_v3_2_scope_budget_v1
budget_receipt_sha256: 20c25c1c348e691bdd24ed69e47b7e0c534dc3c590819442c7b014bb21f2bf1a
approved: true
frozen: true
stage0_authorized: false
automatic_retry: false
```

| Scope | Planner | Execution | Timeout |
|---|---:|---:|---:|
| F1 root | 12/branch | 1/branch | 1200s/branch |
| F2 selected asset root | 12/branch | 1 asset check + 3 branches | 1200s/branch |
| F3 diagnosis+repair+programs | 16/diagnostic, 32/program | 2 diagnostics + 3 programs | 1800s/run |
| F4 layout+common+programs | 256 total | 10 total | 20400s total |

旧v3_1 budget/headroom不是v3_2重试权限。每个v3_2 run仍需独立request/source-lock/authorization/consumption/guard/output。
