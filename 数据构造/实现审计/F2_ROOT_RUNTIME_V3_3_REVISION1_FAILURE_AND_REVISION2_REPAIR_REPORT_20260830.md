# F2 revision-1 failure and revision-2 repair report

Revision-1在task/physical阶段3/3统一失败，planner=0、execution=0。原因不是box/scale/stand布局：三者实际误差仅纳米级；代码错误地把dynamic can的spawn z=0.79 m与60-step settle后的z=0.740628 m要求1e-6相等。罐头XY仅漂移0.027 mm，正常下落49.372 mm并sleep。

Revision-2=`f2_post_settle_dynamic_pose_contract_v3`：planned spawn与静态设施仍严格hash/exact Gate；只在task/physical disposable scene中，以同一actor pose做50×250 Hz linear/angular差分，并要求XY≤5 mm、z drop 0–10 cm、upright、table support height/contact、sleep。Prefix/suffix fresh scene仍由same-current/anchor锁定；罐头已抓起后不再错误套spawn Gate。对象、left arm、inside/on/beside、设施、布局和verifier均不变。

R1的4 scenes cleanup/Guard/GPU4 release全部安全；evidence tree=`6eb7878b…9989`。F2只剩一次revision-2，失败即terminal。
