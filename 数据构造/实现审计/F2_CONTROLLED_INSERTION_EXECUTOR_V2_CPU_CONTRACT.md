# F2 Controlled Insertion Executor V2 CPU Contract

Status: `IMPLEMENTED_AND_CPU_VERIFIED_DISPATCH_INACTIVE`

The new executor is explicitly two-phase:

1. Exact frozen pregrasp/grasp planner inputs → execute → close → 250-frame settle.
2. Runtime geometry match and actual `T_EEF→can` Gate → rebuild and replan lift/preinsert/descend/retreat/neutral from the actual transform.
3. Require 50-frame supported/stable insertion before any opening.
4. Open monotonically at `0.2/0.4/0.6/0.8/1.0`, ten frames per level, then settle 250 frames and return neutral.

Translation/orientation drift limits are 5 mm/50 mrad. Horizontal margin includes 5 mm tracking, 5 mm translation drift, the 50 mrad rotational envelope, and 10 mm safety. The 10 cm gravity drop is not primary. Runtime dispatch and all execution authorizations remain false.

Contract SHA-256: `0b7f55b0e794c8be93b6f347d41d3487b128e1652b800584b2f19199db1f30cc`.
