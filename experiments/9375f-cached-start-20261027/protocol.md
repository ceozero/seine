# EPYC 9375F replacement, 2026-10-27

The 9575F replacement was rejected as out of stock; no replacement instance was
created. Original 9575F files were lost after a controller error; no interim rate
from that server will be published. This available 9375F is the final bounded
replacement: one hour at $1.9808/hour. Even allowing a full billed hour for the
original 9575F ($2.7062), combined listed compute stays under $5.4124.

Single controller with timestamp parsing tested locally and an independent
provider-deletion watchdog. Hardware and memory DIMMs are inspected on arrival.
Official v0.2.39, all 21 1GiB reference parity cases required. Fixed manual screen
at 16,32,48,64 workers, 60 seconds each, streaming kernel and explicit 1GiB pages;
three fresh 120-second confirmations of the highest whole-invocation screen rate.
Whole-invocation completed-hash accounting, full page backing, zero allocation
failures; all screens retained. Power settings unchanged, power not measured.

Then restore original page reservation and test the memory-accounting candidate
from ../9575f-20261027/candidate.patch. This follow-up runs under a real Linux
MemoryMax=192G cgroup to reproduce the memory pressure of a large cached count.
It is a constrained-startup diagnostic, not the stock 384GiB host's performance.
Use independent empty-directory 300-second cold runs baseline then candidate,
then four 180-second cached restarts in baseline/candidate/candidate/baseline
order. Reuse each binary's natural cold cache by copying it to fresh directories;
never rewrite identities or values. Same private-network fixture, unprivileged
account, and no thread/kernel/page/profile overrides. Keep complete evidence.

Only land the one-change candidate if native cached pairs improve, the logged
startup delay is resolved, and cold behaviour shows no material regression.
Otherwise retain the candidate/evidence without changing defaults. Existing
53 adaptive CPU, 66 config and 65 kernel-policy tests passed; real rig exercises
the native paths excluded by the ignored local tests.

Before follow-up, ensure at least 1,370 seconds remain. Reserve three minutes at
lease end for collection and verified deletion. No miner release or restart.

Acceptance thresholds fixed before candidate native measurements: both adjacent
cached candidate/baseline ratios must be positive and their geometric gain must
exceed 3%; candidate cold rate must be at least 97% of baseline. The log must
show prompt streaming selection instead of the diagnosed count-recovery delay.
These gates are screening criteria, not a confidence interval.
