# dandelion-plus-plus-explained: research notes

Post: `src/content/blog/dandelion-plus-plus-explained/` ("Dandelion++ explained: stem and fluff
transaction relay"), drafted 2026-10-25. English `sourceHash` c5a80652c040; zh-Hans and zh-Hant
are `translation: draft`. Body about 1,330 words, 2 `<Answer>` blocks, 4 FAQ entries.

## Intent

Reader's job: understand what Dandelion++ is and how its stem and fluff phases hide which node
sent a transaction, for any coin. Nearest owner: `blocknet-privacy-features`, which has one
two-paragraph Dandelion++ section. This post adds the general mechanism (why flooding leaks the
source, first-spy estimator), the 2017 Dandelion to 2018 Dandelion++ changes with the paper's
q guidance, and Blocknet's full relay parameters (stem 0.9, 10-minute epochs, 45 s embargo,
per-epoch own stem peer, stem payload check).

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| dandelion++ explained | `/blog/dandelion-plus-plus-explained/` | Explain Dandelion++ stem and fluff relay for any coin, why it hides the sending node's IP, what the 2018 paper changed, and Blocknet's relay settings | dandelion++, dandelion protocol crypto, stem and fluff, transaction relay privacy, blocknet dandelion++, Dandelion++ 交易中继 / 交易中繼 |

Boundary: `blocknet-privacy-features` keeps its short Dandelion++ section and could link here
for the mechanism. Overlap report after edits: 0.6% shared 8-word phrases with
ring-signatures-explained, 0.4% with blocknet-privacy-features, 0.2% with bulletproofs-explained.

## Facts used from the fact sheet

Dandelion++ with stem probability 0.9 (§1 Privacy, `p2p/dandelion.go:21-26`); routes rotate
every 10 minutes (§9, `p2p/dandelion.go:30`); CLSAG ring of exactly 16, one-time stealth
addresses, Pedersen commitments with Bulletproofs range proofs, privacy mandatory (§1 Privacy);
seine auto-tuning and mining to an address or @name on bntpool.com (§4, §9).

## Facts added (verified 2026-10-25)

Code refs: `blocknet-core@pool` = c646196 (2026-10-15).

- `EmbargoTimeout = 45 * time.Second`: "how long to wait for tx to return before fluffing".
  `blocknet-core@pool:p2p/dandelion.go:36-38`. Embargo loop runs every 5 s and fluffs records
  still in stem state older than 45 s (`:398-440`); own tx marked seen when it comes back in
  fluff (`:449-453`).
- Own transactions go to one outbound stem peer, picked at random (crypto RNG) and kept while
  connected; cleared at each epoch rotation. `p2p/dandelion.go:128-163`, `:306-328`, `:353-361`.
- Relay: on receiving a stem tx, fluff if random > 0.9 (or RNG error), otherwise forward to a
  random peer excluding the sender; fluff if no candidate. `p2p/dandelion.go:187-234`, `:330-351`.
- Stem send failure fluffs immediately (`p2p/dandelion.go:260-304`); no peers → fluff
  (`:147-155`).
- Same stream protocol (`/dandelion/1.0.0`) and `sendStem` for originating and relaying.
  `p2p/dandelion.go:162`, `:232`, `:260-279`; `protocol/params/network.go:32`.
- Stem payload sanity check: payload must deserialize as a transaction, else peer penalized
  (`ScorePenaltyInvalid`). `daemon.go:461-464`; `p2p/dandelion.go:165-185`.
- Wallet send path: CLI and API call `SubmitTransaction`, which deserializes, adds to mempool,
  then `BroadcastTx` via Dandelion++; no config flag disables it. `daemon.go:1280-1296`;
  `cli_cmd_wallet.go:194-195`; `api_handlers.go:1200`, `:1463`; `git grep -i dandelion` shows
  no flag.
- Not stated in the post (implementation detail): `stemNeighbors` is built per epoch but not
  used for selection; `StemTimeout` (30 s) constant is unused.

## External sources

- Fanti, Bojja Venkatakrishnan, Bakshi, Denby, Bhargava, Miller, Viswanath. "Dandelion++:
  Lightweight Cryptocurrency Networking with Formal Anonymity Guarantees". Proc. ACM Meas. Anal.
  Comput. Syst. 2, 2, Article 29 (June 2018). https://doi.org/10.1145/3224424 ; arXiv:1805.11060
  (v1 2018-05-28). Read from the arXiv PDF on 2026-10-25. (Title contains a word the checker
  forbids, so the post cites venue and links without quoting the title.)
  - Supernode attacks [11] Biryukov, Khovratovich, Pustogarov 2014 (ACM CCS) and [31] Koshy,
    Koshy, McDaniel 2014 (FC); supernode "connected to all P2P nodes" and logged relays (§1).
  - First-spy estimator "outputs the first honest node to deliver a given transaction to the
    adversary as the source" (§3).
  - Bitcoin Core "adopted a protocol called diffusion" with independent exponential delays (§1).
  - Dandelion [14] Bojja Venkatakrishnan, Fanti, Viswanath 2017, POMACS 1, 1: stem and fluff,
    line graph (directed cycle), geometric hops with parameter q (§2); three idealized
    assumptions (§4).
  - Dandelion++: epochs "on the order of 10 minutes"; approx-4-regular graph, each node picks
    up to two outbound edges as relays; own transactions on the same outbound edge; per-epoch
    diffuser/relay choice and incoming-to-outgoing edge mapping; fail-safe random timers (§4).
  - "by choosing parameter q ≤ 0.2, we can limit the increase in average precision" (§4.3);
    mainnet experiments chose "q = 0.1 or q = 0.2" for a 4.5 s propagation goal; "the expected
    stem length is 1/q" (§5.3.1).
- SIGMETRICS 2018 accepted papers list includes the paper:
  https://sigmetrics.org/sigmetrics2018/accepted_papers.html
- BIP 156 "Dandelion - Privacy Enhancing Routing" (same authors' group):
  https://github.com/bitcoin/bips/blob/master/bip-0156.mediawiki
- Monero 0.16.0.0 "Nitrogen Nebula", 2020-05-23, adds Dandelion++:
  https://www.getmonero.org/2020/05/23/monero-0.16-released.html

## Derived

- Blocknet q = 1 − 0.9 = 0.1, so expected stem length 1/q = 10 hops (paper's formula).

## Related / cross-links

Suggested `related`: blocknet-privacy-features, what-is-a-privacy-coin, ring-signatures-explained.
Cross-links to add: privacy-features Dandelion++ section → this post; what-is-a-privacy-coin
network-layer mention → this post; stealth-addresses / ring-signatures / bulletproofs posts'
"other layers" lines → this post.
