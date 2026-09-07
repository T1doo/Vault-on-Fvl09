# F4-B六格登记的纯合并函数

`merge_f4_b(current, report)`只返回新字典和登记一致性检查，不写文件、不发起验收、也不运行GPU。调用前主线程必须独立重算真实终结审计并核对source/raw/Guard/资源证据。报告自hash只能防止字节误改，不是物理成功证明。

合并仅允许F4/B的三个程序×`r_pc/r_inv_motion`六格，必须全部原为pending且没有evidence。它保留其他格子的原内容，要求current恢复、旧pc、motion最终验收和六条终态等价证明齐全，再调用pilot_matrix_audit检查重复raw/current/root及登记字段；拒绝重复登记。

测试使用明确标注的内存假报告，只测合并和拒绝行为，绝不产生真实候选或修改pilot_cells。未来真实登记需先保存审计及原登记快照/哈希，再由主线程单独原子写入、复核，并追加日志。48格完成仍不代表科学Stage1或整个Goal完成。
