# runtime-v3_3 revision-7终止审计、F4 micro通过与revision-8 impact review

## 裁决

`BLOCKED_WITH_REASONS`。F4的A-only micro Gate已经真实通过，但F1仍是唯一完整accepted nonformal root；F2/F3仍未完整通过，F4完整B/C与三程序尚未运行。

## F2

Task/physical与canonical prefix通过；`on` 4/4、`beside` 6/6仅suffix planner通过。`inside`补偿后的第一目标确实逐bit送入planner，但唯一query返回`IK_FAIL`，因此三分支均未执行。0.641mm是盒沿几何余量，不是IK margin，不能用来解释失败。下一版只测试固定XY-only补偿，保留r6已成功IK的z/quaternion，并先修普通planner-false路径不保存compensation receipt的审计缺口。

## F3

三个program的planner、全部V/H realized motion、10mm bottle/assembly planning+runtime geometry均通过，并完成三条真实execution。唯一失败是pre-open contact-free Gate：每program有150条bottle-pad与50条fl7-pad records，但所有impulse精确为0，几何净空分别约10.25–10.27mm和46.18–46.20mm。当前trace没有signed separation/shape identity，不能只凭零冲量静默放行。r8先补这些信号，再把pair presence保留为audit-only，physical hit定义为`impulse>1e-10 or separation<=0`，同时继续强制geometry pass。

## F4 micro

F4-r7通过：A实际上升17.2152mm（门槛15mm），87帧contact fraction=1、break=0、最少双contact count=2；A-table pair前7帧有非零冲量，尾10帧pair仍存在但冲量全0并正确判为physical contact cleared。Preclose、noninterference、common-X tray、same-current/anchor/prefix、250Hz与`3751 actions / 3752 states`全部通过。

该证据只支持A-only micro feasibility与verifier mapping，不是完整F4 root。下一安全F4 scope是已有`F4_block_root_per_revision`：staged A/B/C/AB后运行完整ABC/ACB/BAC，任一步失败即终止。

## Evidence trees

| Family | Files | Tree SHA-256 |
|---|---:|---|
| F2 | 28 | `3cc23996b115d3f23cc3aa2a551ffd2ad7543d7b072fa7581e50027292641cca` |
| F3 | 36 | `43db0df94ca608c03aea5a5366803ce94674d6624cd0eecf50cf13f97ff9a914` |
| F4 micro | 17 | `5139caa8e5c63e75fc6b926c18c74acd9e2fa5846a870860e97b6ea6a6f4d1df` |

Stage0继续禁止；revision-8必须新source/hash/budget/namespace，single-use、无自动retry、recovery=0。
