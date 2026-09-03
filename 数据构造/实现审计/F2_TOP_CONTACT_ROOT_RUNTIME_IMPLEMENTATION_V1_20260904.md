# F2 top-contact development-root runtime implementation V1

日期：2026-09-04  
状态：`IMPLEMENTED_CPU_VALIDATED_GPU_NOT_YET_RUN`

新module：`controlled_multi_future/f2_top_contact_root_runtime_v1.py`  
SHA-256：`56ffd2bd094137052ad062322c3227d9265523d3229fc73bc4794d57b2f6d85b`

实现内容：

- 将已通过微门的provisional `can0+box2+scale0+stand0 / left` binding冻结为selected development binding，保留原asset/layout/cavity/program字节和哈希来源。
- 三program固定为`F2-inside/F2-on/F2-beside`；不做candidate或seed搜索。
- Canonical prefix不再调用旧的all-contact dynamic chooser；只从official `contact8/rotation0/pregrasp0.09m`构建精确pregrasp/grasp，再派生12cm lift。
- Prefix恰好发3 planner queries；执行pregrasp/grasp后先检查5mm/0.05rad tracking hard Gate，失败时在`close_gripper`之前终止。
- close后执行12cm lift，保存post-close/post-lift event boundaries、official raw pose receipt、pose freeze、planner/execution receipts、current/anchor和物理prefix acceptance。
- Suffix、release-safety、inside/on/beside family verifier仍由现有F2 asset-bound controller执行，未改threshold或关系语义。

CPU validation已从实际F2成功微门文件解析出：selected binding SHA=`985515944a97b59621067e662b2e33614ebc08c772de74659c01a1c8ae559f0d`，planned-root SHA=`c2240872aac11ef08c3c54fcc90431a37956ee3d7647780ee35834fe7fcc0361`，prefix精确绑定recipe SHA=`f7270daf416afb1b84e230be7dd2418ac0e5a31d2461943da3bd77c6777cfe5e`。尚未创建scene或使用GPU。
