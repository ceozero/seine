# seineminer.com blog: search landscape and topic backlog

> Snapshot from 2026-10-25, kept for its evidence. Since then: seineminer.com resolves and is live; the owner lifted the post-quantum ban (Faraday's plan may be described, attributed); and the owner chose to write Argon2id topics now despite Faraday. The live, ordered list is `../backlog.md`.

Checked 2026-10-25 between about 00:15 and 01:00 EDT. Sources:

- Live Google SERPs (en/US, `num=20`), fetched through the shared Chrome profile. Google started rate-limiting with "unusual traffic" pages after about 22 queries, so I stopped there rather than solve captchas in the shared profile.
- The WebSearch tool, which uses a different index. It is noticeably weaker on 2026 content.
- WebFetch of the competitor and property pages.

We have no volume data. The demand notes below are inferred from SERP composition, related searches and People-also-ask (PAA) boxes, so treat them as directional only.

---

## 0. Fix before writing anything

| Finding | Evidence | Why it matters |
|---|---|---|
| **seineminer.com does not resolve.** WebFetch returned `getaddrinfo ENOTFOUND seineminer.com`. seineminer.pages.dev works: title "seine — the fastest Blocknet miner", with a `/blog/` link and no posts yet. | Fetched 2026-10-25 | A blog on a domain that doesn't resolve earns nothing. Point DNS at the site, 301 pages.dev → seineminer.com, and set the canonical. |
| **None of our properties appear for "seine miner" or "seineminer".** Google's "seine miner" results are SEAMINER ASICs, Seine River gold mining, and `cardano-miners/seine`. | Google, 2026-10-25 | The brand name has no search equity yet. Always pair "seine" with "Blocknet miner" in titles. |
| **The GitHub repo description is "trawling with my block net".** It shows up verbatim as the SERP title and snippet in WebSearch results. | github.com/zpalmtree/seine, github.com/ceozero/seine | Change it to something like "Blocknet (BNT) Argon2id miner for CPUs and NVIDIA GPUs". This is the cheapest ranking fix available. |
| **blocknetcrypto.com did not appear in any Google SERP I checked**, including "blocknet privacy coin" and "blocknet BNT". The site has no mining instructions and doesn't link to any miner or pool. Its title is "blocknet · zero-knowledge money". | Google; WebFetch of blocknetcrypto.com | The official site isn't carrying the coin's search identity. Ask upstream for a "Mine" link to seine and bntpool. The seine site will have to rank on its own. |
| **The coin isn't listed on miningpoolstats, hashrate.no, whattomine, or Kryptex device pages.** | hashrate.no/coins (no BNT); miningpoolstats home (JS table, no hit); whattomine/Kryptex/hashrate.no rank for every "best CPU for mining" query | Listings are where "what to mine with CPU" traffic goes. Outreach for listings is worth more than any listicle we could write. |

---

## 1. Name collision

### What the SERPs return (Google, 2026-10-25)

| Query | Top results | Our properties |
|---|---|---|
| `blocknet` | WebSearch: docs.blocknet.org, Coinbase/Crypto.com BLOCK price pages, blocknetdx GitHub | none |
| `blocknet mining` | blocknet.org, **blocnet.app** (a different "gem" app), crypto.com BLOCK price, docs.blocknet.org staking guide, blocknetx.io, YouTube "Blocknet: The Sleeper Crypto Pick", investing.com, Binance how-to-buy. Related searches: "Blocknet mining app", "Blocknet mining 2022". | none |
| `how to mine blocknet` | docs.blocknet.org staking, masternodes.com/blocknet, blocknet.org, blocnet.app, Bitget, **coinario.com "How to Mine Blocknet (BLOCK) 2026"** (thin spam that calls BLOCK PoS but also GPU/ASIC-mineable), blockchain-council, r/theblocknet | none. **No correct answer in the top 8.** |
| `blocknet miner` | blocknet.org, a Play Store app, **cassh100k/blocknet-cpu-mining README (#3)**, **powhub.top "BNT 百科 · Blocknet 社区" (#4)**, App Store, a 2017 BitcoinTalk "Is BlockNet really a scam?", a Facebook group, blocknetx.io | none directly. Two third-party pages about *our* coin rank. |
| `blocknet pool` | **github.com/zpalmtree/blocknet-pool (#1)**, blocknet.org, Play Store, **afkpool.com/bnt/miner "BNT Blocknet 矿池" (#4)**, Pangolin listing, public-pool.io, cassh100k README | Our pool *software repo* ranks #1. bntpool.com does not appear. |
| `blocknet wallet` | All old Blocknet: docs, downloads, blocknetdx GitHub, YouTube install, XLite, Tangem | none |
| `blocknet privacy coin` | **github.com/blocknetprivacy/blocknet (#1)**, then old-BLOCK price pages, Elliptic, r/Monero | The upstream GitHub ranks #1. "privacy coin" is the term that disambiguates best. |
| `blocknet argon2id` | cassh100k README (#1), powhub.top (#2), then password-hashing pages, afkpool.com | none |
| `blocknet BNT` | blocknet.org, blocnet.app, predict.blocknet.id, crypto.com BLOCK, Facebook, Coinbase, Barchart, powhub.top/account | none |
| `bntpool` | **Bancor** dominates the results: Etherscan "Bancor: BNT Pool V3", bnBNT, Bancor docs, Lido. powhub.top is #7. | **bntpool.com does not rank for its own name.** |
| `blocknet crypto mining 2026` | Play Store "Block Network", Yahoo BLOCK-ETH, Bitcoin halving news, blocknet.org, **x.com/blocknetprivacy (#7)** | none |

### Google AI Overview (the most important finding)

For `blocknet mining`, the AI Overview says, roughly: *"Blocknet uses Proof-of-Stake (PoS) rather than traditional Proof-of-Work (PoW) mining… originally used PoW for its very first 2,000 blocks, but permanently transitioned to Proof-of-Stake."* It then describes 5,000-BLOCK service nodes and superblocks, and finishes with a paragraph on the Blocnet points app.

So anyone searching how to mine our coin is told by Google that it can't be mined. The WebSearch tool's summaries made the same mistake on most queries: they repeatedly told me "Blocknet is PoS, mining isn't possible" and merged the two projects. Answer engines currently treat **Blocknet as BLOCK**.

### Other collisions

- **BNT = Bancor.** This applies on Google (`bntpool`), on MEXC `BNT_USDT` pages, and in the WebSearch index. cassh100k's guide warns about it. The community GPU miner is literally named "bntminer".
- **The coin is also being called "BLOCK".** A Chinese X post (DogeSwap, x.com/swap_doge/status/2076467744036508045) says "加入 BNTPOOL 挖 Blocknet (BLOCK)". Third-party copy is already spreading the wrong ticker.
- **Near-homonyms:** blocnet.app (Blocnet Points, BNP), blocknetx.io, predict.blocknet.id, a "Block Network" mining app, and Block Inc. (Jack Dorsey). Block Inc.'s Proto mining rigs ate the whole `blocknet faraday upgrade 2027 miners` WebSearch result set.

### Disambiguation guidance for titles and copy

- **Use** "Blocknet (BNT) privacy coin", "Blocknet Argon2id", "mine Blocknet with seine", "bntpool.com". "privacy coin" and "Argon2id" are the two tokens that pulled *our* chain's results up in testing. On first mention, state "the 2026 Argon2id proof-of-work chain, not the 2014 BLOCK/XBridge project".
- **Avoid** bare "BNT" (Bancor), "BLOCK", "$BNT", and bare "Blocknet" in titles.
- Put a short **"Which Blocknet?" box** at the top of every coin-specific post: our chain is PoW, 2 GiB Argon2id, launched 2026, explorer.blocknetcrypto.com. Mark it up as FAQ or definition content. The aim is for answer engines to have a clean, quotable sentence that contradicts the PoS claim.
- Do not disparage the old project. Stick to factual distinction.

---

## 2. Existing content about the new Blocknet: who ranks, and how thin it is

| Asset | What it is | Notes |
|---|---|---|
| **powhub.top** ("BNT 百科 · Blocknet 社区", operated by "pow otc hub", dated 2026-10-20) | Chinese community wiki with a calculator, device table, pool directory, Seine quick start, and wallet/miner/troubleshooting/risk guides, plus a Faraday 2027 section and OTC valuation | **The strongest third-party asset, and it ranks on 4 of our queries.** Its device table has questionable numbers: Ryzen 9 7950X "6–10 H/s", a "Mac mini M6", EPYC 9654 dual "80–95 H/s". It also lists pools: NTMminer (`stratum+ssl://103.54.127.250:3443`), bntpool.com:3333, and Gozero (`bnt.pool.gozero.trade:14444`). An English, measured version would beat it. |
| **cassh100k/blocknet-cpu-mining** (GitHub, 0★) | Safety-first CPU guide for seine + bntpool, with systemd, a tracker, and troubleshooting | Ranks #1 for `blocknet argon2id` and #3 for `blocknet miner`. **Says "GPUs don't help", which is wrong.** It also says the default seine dev fee is 2.5% and bntpool's is 1%. It has no Windows or macOS coverage. |
| **Sebdev43/blocknet-mmpos** (0★, bumped around 2026-06-12) | mmpOS package that wraps seine | Shows rig-OS demand. No HiveOS equivalent was found. |
| **VaniaHilkovets/bntminer** (0★, binary only) | Closed-source NVIDIA RTX 30/40/50 miner for Linux, **5% fixed dev fee**, needs 2.25 GiB of VRAM | The only competing GPU miner found. No published hashrates. |
| **lemo1bot/env-miner-windows** (1★) | Multi-coin Windows bundle that lists Blocknet via ".env Blocknet CPU" and "Seine" | Redistributes or wraps seine. That raises a binary-trust question for users. |
| **ceozero/seine** | Fork of seine | Shows in WebSearch with our README text. |
| **obselate/bntui** (lib.rs) | Rust TUI explorer for the daemon, with mining on/off and thread controls | Confirms the **in-daemon miner** exists. It is the "default" competitor, and seine has to explain why it's better. |
| **AFKPool** (afkpool.com/bnt) | Multi-coin Chinese/English/Russian pool, PPLNS | Ranks #4 for `blocknet pool`. |
| **coinario.com/coin/blocknet/coin-mining** | Auto-generated "How to Mine Blocknet (BLOCK) 2026" | Wrong coin and wrong mechanism, yet it ranks for `how to mine blocknet`. The bar is very low. |
| YouTube | Nothing about our coin. "Blocknet" video results are about BLOCK, such as "Sleeper Crypto Pick" and a Windows wallet install. | Open space. A video embedded in the how-to post would also show in Google video packs. |
| Reddit / BitcoinTalk | None found for the new chain. r/theblocknet and BitcoinTalk threads are about the 2014 BLOCK project. | Low organic social footprint, so there are no forum threads to rank against or link from. Uproar chat (uproar.chat/invite/blocknet) is the official community and isn't indexed. |
| miningpoolstats / hashrate.no / whattomine | Not listed | See section 0. |

**Verdict:** coin-specific intents are near-empty. They're answered by one Chinese wiki, one 0-star GitHub README, and spam. Each coin-specific post we publish has a realistic shot at #1 for its query, but those queries are tiny. Total demand is bounded by awareness of the coin, so the adjacent intents in section 3 have to bring in new people.

---

## 3. Adjacent, higher-volume intents

| Intent cluster | What ranks now (Google, 2026-10-25) | PAA / related searches | Can a niche newcomer compete? |
|---|---|---|---|
| **Most profitable coin to CPU mine / CPU mining 2026** | hashrate.no/cpus, changelly (Aug 2026 listicle: XMR, VRSC, ZEPH, RTM, DERO, VTC, with no Argon2), r/cryptomining "What to CPU mine in 2025/2026", whattomine/cpu, cryptomus, coinledger, poolbay, atomicwallet, suprnova, monero.how, YouTube | "Which coin is the best for CPU mining?", "What CPU is best for crypto mining?", "cpu mining calculator", "cpu mining coins list", "Free cpu mining 2026" | **Not with a listicle.** Calculators and high-authority sites dominate, and a self-serving "best coin" list risks the scaled-content and bias problem. **Get listed** (hashrate.no, whattomine, Kryptex, changelly outreach) and publish one honest, measured piece instead (backlog #13). |
| **Best CPU for mining** | pool.kryptex.com/device/cpu, herominers, techradar, xmrig.com/benchmark, hashrate.no; Google shows a product carousel (5900X, 7950X, 7960X, EPYC 9754/9654) | | Hard for the generic query. Winnable as "best CPU for **Argon2id / Blocknet** mining", using our measured table. |
| **Mining on Mac / Apple Silicon** | App Store apps, a 2017 Reddit post, daytrading.com, bitcoinwiki MacMiner, Macworld, a GitHub unMineable wrapper, koinly; for M4: r/MoneroMining "M4 Mac Mini Mining", aldomedia, bitcointalk "M4 PRO", imineblocks | "Are Macbooks good for crypto mining?", "How long will it take to mine 1 Bitcoin on a laptop?", related "Mac m4 mining", "Mac mini M4 mining", "Crypto mining apple silicon", "Mac Studio crypto mining", "Best crypto to mine on mac" | **Yes. This is the best adjacent bet.** The results are thin and Bitcoin-centric. Our measured M4 Max at 30.9 H/s puts a Mac within reach of a Zen 4 EPYC on Argon2id, whereas Kryptex shows an M4 Pro as weak on RandomX (6.82 kH/s). That's a genuine, verifiable story. Apple-to-apple numbers for M1–M4 tiers are needed. |
| **Mining on a laptop** | Reddit, emcd, a Cointelegraph/TradingView piece, Ledger, YouTube, Medium, Quora, all Bitcoin-centric | "Can I do crypto mining on my laptop?", "What is the best crypto to mine on a laptop?", "Which laptop is best for crypto mining?" | High volume and low conversion, and the content carries a hardware-wear liability. P3, and only with thermal and power data. |
| **Huge pages** | xmrig.com/docs/miner/hugepages, r/MoneroMining, Medium "30% increase", Binance Square, BitcoinTalk, Hiveon forum, redips | "Huge pages xmrig", "Huge pages Windows", "Xmrig huge pages unavailable", "Enable huge pages Windows 11", "Enable 1GB pages xmrig" | The generic term belongs to XMRig. Winnable for the "2 GiB per hash" variant (are 1 GB pages worth it when each hash touches 2 GiB?) and for Windows "Lock pages in memory" troubleshooting tied to seine. Medium. |
| **NUMA / dual-socket** | xmrig GitHub issues #177 and #1669, r/MoneroMining, the xmrig RandomX optimization guide, ServeTheHome forum, an Intel community thread | "Xmrig numa dual socket benchmark" | Low volume, but the results are stale (2017–2022 issues) and the audience owns big hardware. seine just landed NUMA/L3 spreading (commit 63d1c9a, 2026-10-24). Winnable with before/after data. |
| **Argon2id as proof of work** | RFC 9106, Wikipedia, a LinkedIn post, IETF draft, password-hash tools, StackExchange | "Is Argon2 still secure?", "Is Argon2 better than SHA256?", "Can you explain what Argon2id is and what it does?"; related "Argon2id proof of work github" | **Yes.** The results are dominated by password-hashing content, and no page explains Argon2id *as PoW* for miners. Other Argon2id PoW coins (Bitweb BTE, BTC09, Perihelion) only have whitepapers. |
| **Memory-hard PoW** | crypto.stackexchange, neptune.cash article, IACR 2025 paper, Wikipedia, privatecaptcha blog, ACM paper | | Academic results. An explainer could rank lower down the page. Fold into the Argon2id explainer rather than writing a separate post. |
| **RandomX vs Argon2** | xmrig issue #1687, an arXiv password-hashing study, a Reddit chukwa thread, RandomX issue #101, Trail of Bits 2019, OSTIF audits | | **Yes.** Thin and old, with no measured same-machine comparison anywhere. |
| **RTX 5090 / GPU mining** | whattomine, NiceHash, minerstat, rabidmining, hashrate.no, evezone | "Is RTX 5090 good for crypto mining?", "Which coin is best to mine with a GPU?", "How to earn money with RTX 5090?", "Best coin to mine with 5090" | Calculators own the generic query. "Mine Blocknet on RTX 5090/4090" is winnable, but our 5090 numbers are modest (about 8 H/s in the local tuning doc), so frame it honestly as CPU+GPU additive rather than "GPU coin". |
| **AVX-512** | 2024 Qubic-era news (TechRadar, TechSpot, KitGuru, FPS Review) and Phoronix | | Old news coverage with no measured Argon2id AVX2-vs-AVX-512 data. Niche, but we can be the only measured source. |
| **Privacy coin mining** | WebSearch: Monero dominant, DERO second, Zcash is ASIC; listicles from tokentax, oneminers, cryptomus | | Google rate-limited before I could check this query. The term is already brand-sensitive and our claims are constrained, so rely on factual "Blocknet vs Monero mining" comparisons only (that's backlog #12, not a "best privacy coin" list). |
| **Antivirus flagging miners** | Generic Defender-exclusion pages, a Kaspersky xmrig thread | | Evergreen troubleshooting for any miner. seine's reproducible builds and SHA256 checksums give us a unique "how to verify" angle. |

---

## 4. Search-intent shapes and questions found

- **How-to:** how to mine Blocknet; mine Blocknet on Mac / Windows / Linux / HiveOS / mmpOS; set up huge pages; run seine as a service.
- **Comparison:** Argon2id vs RandomX; CPU vs GPU for Blocknet; seine vs the in-daemon miner vs bntminer; Blocknet pools compared; Blocknet BNT vs Blocknet BLOCK.
- **Troubleshooting:** hashrate shows but the pool doesn't (powhub's checklist covers this); "paid stays 0" for the first 5–6 h (from cassh100k); a 1 GB VPS can't run it; rejected or stale shares; huge pages unavailable; antivirus quarantine; port 3333 blocked.
- **Explainer:** what Argon2id PoW is; why 2 GiB per hash; what the Faraday upgrade means for miners; how PPLNS works.
- **PAA questions seen:** "Which coin is the best for CPU mining?" · "What CPU is best for crypto mining?" · "Are Macbooks good for crypto mining?" · "Can I turn my laptop into a crypto miner?" · "What is the best crypto to mine on a laptop?" · "Is crypto mining still profitable in 2026?" · "Can you explain what Argon2id is and what it does?" · "Is Argon2 better than SHA256?" · "Is RTX 5090 good for crypto mining?" · "Which coin is best to mine with a GPU?" · "What is the current price of Blocknet?" (this one is on blocknet queries, and it's the BLOCK price).
- **Questions Blocknet newcomers will ask** (inferred from the powhub and cassh100k guides): How much RAM per thread? Why is my pool hashrate lower than local? When do I get paid? Where do I get a wallet address? Is there a market or price? (Don't answer with price claims.) What happens at Faraday?

---

## 5. Prioritized backlog

Priority reflects (demand reachable) × (chance to rank) × (conversion to seine or bntpool) ÷ effort. **Low-confidence demand** is flagged ⚠. Each row owns one intent. The "nearest-overlap risk" column names the sibling page to keep out of its lane.

| # | Pri | Proposed slug | Primary keyword cluster | Search job (one sentence) | Supporting phrases | Unique evidence needed | Nearest-overlap risk |
|---|---|---|---|---|---|---|---|
| 1 | P1 | `/blog/how-to-mine-blocknet` | how to mine blocknet; blocknet mining guide; blocknet miner | "I heard about the Blocknet privacy coin. Give me the fastest correct path from zero to accepted shares." | mine Blocknet BNT, Blocknet Argon2id miner, bntpool setup, first share, payout timeline | Real end-to-end run on Windows, macOS and Linux with screenshots or video; measured time-to-first-share; the actual PPLNS window, min payout and confirmation count from bntpool; a "Which Blocknet?" box | The README and docs quick start (keep the blog version narrative and cross-platform, and canonical docs for flags), and #2 |
| 2 | P1 | `/blog/is-blocknet-proof-of-stake` (title: "Blocknet (BNT) vs Blocknet (BLOCK): two different coins") | blocknet proof of stake; can you mine blocknet; blocknet BNT vs BLOCK; blocknet bancor BNT | "Google says Blocknet is PoS and can't be mined. Which Blocknet is this, and can I mine it?" | blocknet privacy coin, blocknet 2026, BNT ticker Bancor, blocknetcrypto vs blocknet.org | Chain facts (genesis date, PoW params, block time) with explorer links; quotable one-sentence definitions; FAQ schema. No criticism of the other project. | #1 (don't repeat setup steps; link out) |
| 3 | P1 | `/blog/blocknet-mining-hardware-hashrate` | blocknet hashrate; best CPU for blocknet mining; best hardware for argon2id mining | "Which machine should I mine Blocknet on, and what H/s will it actually do?" | EPYC, Ryzen, Threadripper, Apple M-series, Graviton, RTX 4090/5090, H/s per watt, RAM per thread | Benchmark table with method (repeated runs, host preflight from `benchctl.py`), wall power, and consumer chips (7950X, 9950X, 9950X3D, 14900K, base M4) to correct powhub's numbers | The site's `/performance` page. Either make this the human-readable buyer's guide and keep `/performance` raw, or merge them and pick one canonical. Also #6 and #7. |
| 4 | P1 (time-bound) | `/blog/blocknet-faraday-upgrade-miners` | blocknet faraday; blocknet hard fork 2027; blocknet upgrade mining | "What do I have to change on my rigs for Faraday, and when?" | activation height 103,680, update seine, pool switchover, old builds stop at fork height, new PoW performance | Final upstream PoW spec; a seine release that supports Faraday; pre/post hashrate on the same hardware. Publish only once the spec is final, around Jan 2027. Describe it as the scheduled network upgrade, attribute any post-quantum plans to blocknetcrypto.com, and link the official notice. | The pool's own announcement and blocknetcrypto.com (link to them and don't restate consensus rules) |
| 5 | P1 | `/blog/mine-blocknet-nvidia-gpu` | blocknet gpu mining; mine blocknet rtx 5090 / 4090; argon2id gpu miner | "Can my NVIDIA card mine Blocknet, how much does it add, and what VRAM do I need?" | 2 GiB VRAM per lane, CPU+GPU together, Windows bundled CUDA runtime, Linux NVRTC, Blackwell kernels, dev fee comparison | Per-card H/s for 3060, 3090, 4090 and 5090, lanes vs VRAM, power draw, CPU+GPU additive totals; a factual fee comparison (seine 1% on bntpool vs bntminer's disclosed 5%). This also corrects the "GPUs don't help" claim. | #3 (keep #3 as the cross-hardware table and this one as setup and expectations) |
| 6 | P2 | `/blog/crypto-mining-on-mac-apple-silicon` | mining on mac m4; mac mini mining; crypto mining apple silicon; best crypto to mine on mac | "Is my M-series Mac actually any good for mining, and how do I start?" | M1/M2/M3/M4 Pro/Max, unified memory bandwidth, Metal, thermals, Mac Studio, Mac mini | M-series tier table on Argon2id; same Macs on RandomX via XMRig for contrast; fan and thermal data; 16 GB vs 36 GB RAM thread limits | #3 (summarize Macs there and link here for depth) |
| 7 | P2 | `/blog/argon2id-proof-of-work-explained` | argon2id proof of work; argon2id mining; memory-hard proof of work | "What is Argon2id doing when it's used for mining, and why 2 GiB?" | Argon2id vs Argon2d, t=1 p=1 2 GiB, memory bandwidth bound, ASIC resistance (careful wording), RFC 9106 | Diagram of a hash; measured scaling vs memory channels; profiler data showing bandwidth saturation | #8 |
| 8 | P2 | `/blog/argon2id-vs-randomx` | randomx vs argon2; blocknet vs monero mining; argon2id vs randomx cpu | "I mine Monero. How does Argon2id differ, and which of my machines suit which?" | L3 cache vs DRAM bandwidth, X3D chips, thread count, RAM needs, huge pages differences | Same-machine XMRig RandomX vs seine Argon2id on 4–6 hosts (Zen 4/5, X3D, Apple, Graviton, Xeon). Factual comparison only, with no privacy-superiority claims. | #7 (keep the explainer and the comparison separate) |
| 9 | P2 | `/blog/how-much-ram-to-mine-blocknet` | ram per thread mining; blocknet ram requirement; argon2id 2gb per thread | "How many threads can I run with my RAM, and why did my 1 GB VPS die?" | memory channels, dual vs quad channel, swap, OOM, thread sizing, VPS mining | Thread-scaling curves on 2-channel vs 12-channel boxes; auto-tuner decision logs | #1 and #3 (they should mention 2 GiB per thread in one line and link here) |
| 10 | P2 | `/blog/huge-pages-argon2id-mining` | huge pages mining; enable 1GB pages; huge pages windows 11 mining | "Should I enable huge pages for Argon2id mining, and how on Linux and Windows?" | Lock Pages in Memory, vm.nr_hugepages, 1 GB pages, THP, "huge pages unavailable" | A/B gain with 2 MB vs 1 GB vs off on several hosts; the RAM-reservation tradeoff (from the existing Linux huge pages guide) | Repo huge-pages doc (the blog should explain the why and the data, and the docs should hold the commands), and #11 |
| 11 | P2 | `/blog/numa-dual-socket-epyc-mining` | numa mining; dual socket epyc mining; epyc 9654 mining | "I have a dual-socket or high-core server. How do I avoid losing hashrate across NUMA nodes?" | NPS settings, L3 groups, memory interleave, thread pinning, Graviton/Ampere | Before/after for the NUMA/L3 spreading change (commit 63d1c9a); NPS1 vs NPS4 runs; the field EPYC data | #10 and #3 |
| 12 | P2 | `/blog/blocknet-mining-pools` | blocknet pool; blocknet mining pool list; bnt pool pplns | "Which Blocknet pools exist, and how do their fees and payouts compare?" | bntpool, AFKPool, Gozero, NTMminer, PPLNS window, min payout, solo mining | A verified table of fees, schemes and min payouts for every pool, with dates. **Disclose that we run bntpool.** Include solo/direct mining as an option. | bntpool.com's own FAQ, and #1 |
| 13 | P2 ⚠ | `/blog/is-cpu-mining-worth-it-2026` | cpu mining 2026; is cpu mining profitable; cpu mining worth it | "Honestly, is CPU mining worth doing in 2026 on hardware I already own?" | electricity cost, idle hardware, coins per day, home-office heat | Measured wall power and coins per day on 4–5 everyday machines. No price predictions, and not a "best coins" listicle. | Listing outreach (hashrate.no, whattomine) covers the "what to mine" intent better. Overlaps #3. |
| 14 | P2 | `/blog/blocknet-wallet-address-for-mining` | blocknet wallet; blocknet address; blocknet BNT wallet | "Where do I get a Blocknet (BNT) address to mine to, and how do I keep keys off the rig?" | official GUI/CLI wallet, seed backup, watch balances, never put keys on miners | Walkthrough of the official wallet with checksum verification; address format examples | blocknetcrypto.com and upstream docs should own the wallet manual, so keep this miner-focused and link to them. Also #2. |
| 15 | P3 | `/blog/seine-pool-shows-zero-hashrate` | pool hashrate lower than local; shares rejected; miner login failed | "seine says I'm hashing but the pool shows nothing (or lots of rejects). What's wrong?" | port 3333 blocked, stale shares, clock skew, worker names, paid shows 0 | Real log excerpts and error strings from seine and the pool; control API checks | Docs troubleshooting section (pick one home; the blog post works if docs link to it) |
| 16 | P3 | `/blog/antivirus-flags-crypto-miner` | windows defender crypto miner; antivirus deletes miner; is seine safe | "My antivirus quarantined the miner. Is it malware, and how do I verify it?" | reproducible builds, SHA256 checksums, Defender exclusions, unofficial repacks | Step-by-step checksum verification; reproducible-build instructions; a warning about third-party bundles (env-miner, forks) | #15 |
| 17 | P3 ⚠ | `/blog/mine-blocknet-hiveos-mmpos` | hiveos blocknet; mmpos blocknet; blocknet rig os | "How do I run seine on my rig OS fleet?" | flight sheet, custom miner, Prometheus metrics, control API | A working HiveOS custom-miner package (none exists) plus the community mmpOS package | Repo docs |
| 18 | P3 ⚠ | `/blog/avx512-mining-zen5` | avx512 mining; zen 5 mining performance; avx2 vs avx512 | "Does AVX-512 or Zen 5 actually help mining, measured?" | kernel autoselect, Intel vs AMD, 9950X vs 7950X | Kernel A/B, AVX2 vs AVX-512, on Zen 4/Zen 5/Xeon, from the autotuner | #3 and #11 |
| 19 | P3 ⚠ | `/blog/mine-crypto-on-laptop` | can you mine crypto on a laptop; best crypto to mine on laptop | "Is it OK to mine on my laptop, and what will it do to it?" | thermals, battery, throttling, background priority | Thermal and power logs on 2–3 laptops; a conservative-settings preset | #6 (Mac laptops) |

### Ranking rationale and confidence

- **Top 5 (#1–#5):** these are the only intents where searchers are already looking for *our* coin, and right now Google either answers wrongly (AI Overview says PoS) or answers with thin third-party pages. They're cheap to win and convert directly. Their demand is small and grows with the coin's awareness.
- **#6–#8** are the main *acquisition* bets: real volume, stale or wrong-framed SERPs, and data only we have. #6 (Mac) has the clearest volume signal from its related-search breadth.
- ⚠ = demand not evidenced by SERP signals (no PAA, few related searches) or dependent on rig-OS adoption.
- **Things deliberately left off the list:** a "best coins to CPU mine" listicle (scaled-content and bias risk; outreach is better); per-CPU permutation pages such as "mine Blocknet on 7950X" (that's what the #3 table is for); price or profitability-calculator posts (no public market, and price content is the wrong lane for a miner site); "most private" or "untraceable" comparisons.

### Non-blog actions with outsized impact

1. Fix seineminer.com DNS, canonicalize away from pages.dev, and submit to Search Console.
2. Rewrite the GitHub descriptions for seine and blocknet-pool with "Blocknet (BNT) Argon2id miner/pool".
3. Get the coin and seine listed on miningpoolstats, hashrate.no, whattomine and Kryptex device pages; pitch changelly or other 2026 CPU listicles with our measured data.
4. Ask upstream to add a "Mine" link on blocknetcrypto.com to seine and bntpool.com.
5. bntpool.com: add a crawlable title and description containing "Blocknet (BNT) mining pool". WebFetch got only the title "Blocknet Mining Pool" and no indexable body text, so the page is likely JS-rendered.
6. Offer powhub.top (CN) and cassh100k corrections: GPU support and measured numbers. These are the pages ranking for our terms today.
