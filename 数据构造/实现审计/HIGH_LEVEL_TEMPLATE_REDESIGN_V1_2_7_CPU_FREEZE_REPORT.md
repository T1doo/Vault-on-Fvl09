# High-Level Template Redesign V1.2.7 CPU Freeze

Status: `CPU_SOURCE_SNAPSHOT_FROZEN_F4_A_ONLY_PHYSICAL_READY`

- Active full suite: `709/709`, 246.921 s.
- Review-snapshot full suite: `709/709`, 369.186 s.
- Active/snapshot source: 268 Python files, byte-equal, tree/source SHA-256 `63f90a8d37283e3ff8f68df175115b757858d96a98acc7ca55be524839115b07`.
- Active/snapshot tests: 132 Python files, byte-equal, tree SHA-256 `c48b7057d0c7efb4f9eee180c2c984a8aa73651e96c06c19c0628588f03462f4`.
- Parent authorization SHA-256: `39b9e19d894c0b96effc769234cf813c0c7f1b76ab5ec4559dfe8e3f4e27e134`.
- Registry SHA-256: `fde4e2b586b196ec88df01eaeda1ed65af759e89f2e8417bdb915d2a3ffa31ef`.
- Machine report SHA-256: `36408ddc333baabcc540f6be2f52adc0a300e2f3b2ee0b635c1af5f748f94505`.

The selected r01 A-only scope executes the common-X prefix first with the right arm, then executes one real A placement with the frozen left-arm Stage-B targets. It verifies A slot/support/stability, common-X and B/C preservation, selected gripper open, and left-arm neutral return. Budget: 32 planner queries, one physical attempt, no retry/recovery.

Execution remains constrained to fresh-idle physical GPU3 serially. Stage 1, formal collection, training, H-reveal, compression, and π0.5 remain unauthorized.
