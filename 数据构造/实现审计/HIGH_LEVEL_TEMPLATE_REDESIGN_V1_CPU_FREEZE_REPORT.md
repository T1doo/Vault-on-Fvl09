# High-Level Template Redesign V1 CPU Freeze

## 结论

当前状态为 `CPU_SOURCE_SNAPSHOT_FROZEN_GPU_NOT_RUN`。F2/F3/F4 高层分层候选、真实adapter、planner/physical runner、single-use authorization、Guard v2.4 与候选选择回执链均已实现并在 CPU 层冻结；尚未签发或消费任何 GPU authorization，未运行 SAPIEN/CuRobo GPU job，未生成新 trajectory。

## 候选范围

- F2：12 个 `(can, box, arm)` Stage-A planner candidates，最多 3 个低rank planner-pass candidates 可进入 one-attempt inside physical。
- F3：4 个官方 bottle assets、8 个gripper-region/arm tuples，最多 4 个低rank planner-pass tuples 可进入 Level-2 physical。
- F4：8 个source-layout/arm/grasp-policy Stage-A planner candidates；只有最低rank full pass 才可解锁 Stage B。
- F1：保持 5/5 roots、15/15 trajectories 的 frozen reference，本轮不重跑。

## 验证

- Focused regression：35/35。
- Active full suite：702/702，254.672 s。
- Review-snapshot full suite：702/702，251.010 s。
- Active/snapshot source：268 Python files，byte-equal，tree SHA-256 `dc14a21c03747102602c02951407a198d9e6d3af256ac421d4660fb332102b68`。
- Active/snapshot tests：132 Python files，byte-equal，tree SHA-256 `7a71516270581fc173338e0d0613636a96cfdd3088d00071e33130940e964185`。

## 合同 Hash

- F2：`a43be1b35a96352096da383622d6e14efc675e7c2db6a5d3d922a67d21e550b5`
- F3：`2543c756659dd84c61e258abc6298e34df70e9895bd3e7d4b6f61cd856516516`
- F4：`5b9128fda11b52428f9e0a342d59b953d489432c60cbdbe1911ae904e9ae7341`
- Parent：`be707d553fc059c48ef2225ca87f8a897bf68f63336e4786a761603ab4fc4ee1`
- Parent authorization：`c3c1703bc3a11a0567fa7567a82dbb9a172bb34a286add24825e4daa0140b1cc`
- Registry：`b09637582dd194a48d6e1d36eb7eac0dc34374d0c7aadafb73a06b60d68a1b05`
- Report payload：`b600e5bda9395329049d8cdbcec86ef4f92bee90088eb7c35f49e82fed2898f3`

## 授权边界

Stage 1、360 formal、训练、H-reveal、compression 和 π0.5 仍未授权。下一安全步骤是提交并 push 这个 CPU freeze，然后从 published HEAD 签发 28 个 source-hash-bound planner candidate bundles。
