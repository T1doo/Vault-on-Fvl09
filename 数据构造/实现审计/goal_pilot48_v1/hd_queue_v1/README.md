# Finite serial HD display queue

This main-owned queue renders only remaining accepted F1/F4 saved-state videos.
It never runs task plans, task actions or collection; each item has its own
fresh-idle GPU Guard/UUID/lease, finite 1800-second child and 1980-second lease
reservation. One GPU job at a time. All failed attempts retain their receipts.

`--prepare` freezes the remaining source items and renderer hashes, without
reserving resources. Running the frozen plan checks the private Vault/main
remote, then reserves, preflights and publishes each exact job manifest before
launch. It stops on failure, busy/no-Guard outcome, unknown accounting, changed
source or publication failure. No automatic retries or silent item skipping.

While running, this queue is the sole writer of the Goal budget/STATE. The main
assistant may read its CURRENT/events and inspect completed videos, but must
not concurrently modify those ledger/state files. Guard receipts retain GPU
pre/post snapshots and owned process cleanup. A STOP_AFTER_CURRENT file stops
before another job; interrupting the queue signals only its own scheduler
process group and lets Guard perform owned GPU cleanup.

Completed output is **pending visual review**, not accepted scientific data.
Videos are not automatically copied to the demo directory or called visually
approved. The main assistant reviews and publishes the finished MP4s separately.
Original accepted raw/video files and their success status remain immutable.
