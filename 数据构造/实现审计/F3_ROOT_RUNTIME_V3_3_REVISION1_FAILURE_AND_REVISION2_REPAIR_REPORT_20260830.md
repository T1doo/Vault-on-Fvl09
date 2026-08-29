# F3 revision-1 failure and revision-2 repair report

Revision-1完成task/physical 3/3与candidate freeze，在canonical shared-first-V后被物理Gate截住；planner=16、suffix/execution=0。Immutable trace复算：EEF +54.572 mm pass，负向39.579 mm（距40 mm差0.421 mm）；bottle负向43.064 mm、contact fraction1.0、break0，但orientation drift57.191 mrad>50 mrad，grasp-transform最大orientation drift60.566 mrad。最后50帧PhysX component velocity与同一actor pose差分明显不同，证明旧流混用了body/COM frame。

Revision-2=`f3_pose_consistent_time_dilated_closed_loop_v2`：V仍±z/55 mm，H仍±x/50 mm，程序仍VVHH/VHVH/VHHV、shared first V、left arm/bottle/pad/verifier不变。每个V/H固定7个targets `[+.5,+1,0,-.5,-1,-.5,0]`，每target hold50帧，以降低110 mm长跨越的endpoint lag/旋转滑移；Gate速度改为同一saved actor pose的250 Hz linear+angular差分，PhysX component速度连同type/frame provenance只作audit。Planner envelope从55变为95，仍低于160。

R1的5 scenes、GPU5、cache/lease/source cleanup全部安全；evidence tree=`d70d331c…aea04`。F3只剩一次revision-2。
