# CPU autotuning and Stratum — October 26, 2026

## Intent and boundaries

- `seine-automatic-cpu-tuning`: explain productive CPU tuning, changing thread
  counts, memory response, cache reuse and deliberate overrides. Installation,
  hardware selection, RAM capacity, huge-page reservation and dashboard reference
  remain owned by their existing guides. No benchmark or speedup claim is added.
- `stratum-mining-protocol`: explain the miner/pool/node conversation and the
  sequence from connection through login, jobs and submissions. Setup, share
  troubleshooting, difficulty mathematics and payouts remain separate guides.
- No rented hardware, mining runs or competitor comparisons were needed.

## Evidence

Public release rechecked with the release-facts live validator: v0.2.36,
published October 26, 2026 at 11:34:54 AM EDT. Release commit:
`f3c8175eac0e01cd31870372b2c4989a598044d3`. Pending master tuning behavior
is not presented as released behavior.

- `seine@v0.2.36:src/miner/adaptive_cpu.rs`: productive baseline/candidate/baseline
  samples, warm-up, invalidated comparisons, compatible cache seed, dynamic
  memory budget and preservation of a learned higher count during pressure.
- `src/miner/adaptive_kernel.rs`, `src/config.rs`, `src/miner/mod.rs`: CPU
  instruction eligibility, alternating kernel/count trials, runtime boundaries
  and explicit tuning switches. The article deliberately avoids a numerical
  profile threshold: release documents disagree about a 99% policy, and an
  architecture-neutral summary is sufficient for this article.
- `docs/guides/configuration.md`, `docs/MINER_FLAGS.md`,
  `docs/guides/autotuning.md`: default cache filenames, data directory, explicit
  `--threads`, tuning flags and manual +/- restarts. Automatic CPU changes retain
  the pool connection and GPU backends; manual +/- has different behavior.
- Linux HugeTLB arena release returns pages to the OS reservation; the miner does
  not resize that reservation. The existing huge-pages guide owns that procedure.
- https://github.com/zpalmtree/seine/blob/v0.2.36/docs/guides/autotuning.md
- https://github.com/zpalmtree/seine/blob/v0.2.36/docs/MINER_FLAGS.md
- `blocknet-pool@6521e7c6991629cf1bf364b5b5afea597b6999e0`:
  `crates/pool-common/src/protocol.rs` defines login/submit, request IDs,
  payout address, worker, protocol version, capabilities and submitted hash fields.
  The pool's internal protocol version is not claimed to be Bitcoin Stratum V2.
- Same revision `crates/pool-runtime/src/jobs.rs`: MinerJob identifiers,
  header_base, target, network_target, difficulty, height and nonce range.
- Same revision `crates/pool-runtime/src/stratum.rs`: newline-delimited JSON,
  login acceptance, job delivery/updates, vardiff and submission replies.
  `engine.rs` separates accepted from verified work and routes block candidates
  upstream. A response is not a block or completed payout.
- `seine@v0.2.36:src/pool.rs`: compatible client session and reconnect behavior.
- https://github.com/zpalmtree/blocknet-pool/blob/6521e7c6991629cf1bf364b5b5afea597b6999e0/crates/pool-common/src/protocol.rs

## Graphics and translations

Original CPU SVG depicts A/B/A comparison and memory checks. Original Stratum
cover depicts miner/pool/node message directions using literal protocol labels.
Both are explanatory diagrams, not measured performance or fabricated screenshots.
The existing list layout is retained. The active model authored all 19 translations
for each article; metadata remains `translation: draft`. No independent linguistic
review is claimed or required for this publication.

## Verification

Strict content checks pass for both complete language sets. Maximum English
8-word overlap: CPU article 0.8% with RAM planning; Stratum 0.0% with existing
articles. The related-guide links establish distinct intent and navigation.
Seine tests: 5 passed; pool frontend tests: 21 passed. No runtime code changed.
Build reports, Windows shared-browser desktop/mobile captures, final source
revisions and live verification are recorded at the stable showcase:
http://localhost:8874/autotuning-and-stratum/

Pool publication uses `--api-only`; service identity checks record that Stratum,
monitor and recovery remain running. This batch does not upgrade running miners.
