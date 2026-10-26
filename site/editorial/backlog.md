# Backlog

Researched topics not yet written, in priority order. Batch 1 (2026-10-25) took the hardware,
Mac, Argon2id, what-is-Blocknet, Blocknet ID and privacy topics; pool-side topics went to the
bntpool.com blog. Each owns one search job; check
`keyword-map.md` before starting, and move the row there when the post is published. Evidence
and SERP notes for each topic are in `research/2026-10-keyword-research.md`.

The owner chose (2026-10-25) to write Argon2id-specific posts now, for the traffic before the
Faraday upgrade (planned ~2027-02-16). Date them, and plan a rewrite or retirement when the
proof of work changes.

| # | Slug | Primary cluster | Search job | Evidence needed |
|---|---|---|---|---|
| 2 | `argon2id-vs-randomx` | randomx vs argon2; blocknet vs monero mining | How Argon2id differs from RandomX for a Monero miner, and which machines suit which | Same-machine XMRig vs seine runs on 4-6 hosts |
| 3 | `how-much-ram-to-mine-blocknet` | ram per thread mining; argon2id 2gb per thread | How many threads my RAM allows, and why a 1 GB VPS fails | Thread-scaling on 2-channel vs 12-channel machines |
| 4 | `blocknet-mining-pools` | blocknet pool; blocknet mining pool list | Which pools exist and how fees and payouts compare | Dated table of every pool; disclose that we run bntpool.com |
| 5 | `blocknet-faraday-upgrade-miners` | blocknet faraday; blocknet hard fork 2027 | What miners must change for Faraday, and when | Final public spec and a seine release that supports it; publish around Jan 2027 |

Dropped 2026-10-25 per owner: a BNT-vs-BLOCK explainer (assume readers know Blocknet) and
"is CPU mining worth it" (invites an unfavorable verdict).

## Blocknet topics (general blog)

Coin-level posts that build search presence for Blocknet itself and link to seine and
bntpool.com. Facts come from fact-sheet section 1; demand is unverified (no SERP check yet), so
check search results before drafting.

| Slug | Primary cluster | Search job |
|---|---|---|
| `blocknet-faraday-upgrade` | blocknet faraday; blocknet post-quantum | What the planned upgrade brings, attributed to blocknetcrypto.com |

Low-confidence demand, revisit with Search Console data: HiveOS/mmpOS packaging, AVX-512 on
Zen 5, laptop mining.

## Off-site work that matters as much as posts

- Get Blocknet and seine listed on miningpoolstats, hashrate.no, whattomine and Kryptex (deferred
  by the owner on 2026-10-25; requests go out from the owner's accounts).
- Ask upstream for a "Mine" link from blocknetcrypto.com to seineminer.com.
- Give bntpool.com a crawlable title and description ("Blocknet mining pool").
- Rewrite the seine and blocknet-pool GitHub descriptions with "Blocknet miner/pool".
- Offer corrections to the pages ranking for our terms (powhub.top, cassh100k's guide).

Covered 2026-10-25: zero pool hashrate and connection errors now belong to the expanded
[bntpool tracking guide](https://bntpool.com/blog/track-your-miner-on-bntpool/#zero-hashrate),
including all 20 languages. Do not create a competing Seine article.

Published 2026-10-25: `mine-blocknet-nvidia-gpu` owns NVIDIA setup, runtime diagnosis, accepted-share verification and the measured RTX 5090 GPU-only/CPU-plus-GPU comparison. See `batches/2026-10-nvidia-guide/research.md`. Other cards, including RTX 4090, still need their own measurements before adding results.

Published 2026-10-25: `antivirus-flags-crypto-miner` owns Windows download warnings, official-release checksum verification and reporting unresolved detections. It includes an actual v0.2.26 Windows PowerShell verification record and release-assets capture.
