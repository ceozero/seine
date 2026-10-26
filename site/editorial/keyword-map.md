# Keyword ownership map

Which seineminer.com URL owns which search intent. It records editorial intent, not current
rankings. The build fails if a published post has no row here.

## Rules

1. Each URL owns one primary keyword cluster and one distinct search job.
2. Read this map before proposing, drafting, renaming or retargeting a post.
3. A supporting phrase may appear naturally on related pages, but only its owner optimizes its
   title, H1, description and core answer around it.
4. Broad hubs summarize and route; narrow spokes answer one task in depth. Their jobs differ.
5. Don't retarget a URL away from its cluster to chase a broader term. Add a new URL only when
   the intent is genuinely different; otherwise strengthen the owner.
6. An ownership change updates this file in the same commit, with the old owner, new owner,
   overlap risk and redirect plan.
7. Translations inherit their English row. A Chinese-only target needs its own row naming the
   Chinese phrase (for example 挖矿 / 挖礦 variants).

## Name collisions

"Blocknet" also names an older project (BLOCK token) and "BNT" is Bancor's ticker, so titles
pair "Blocknet" with "mining", "miner" or "Argon2id" rather than standing alone. Posts don't
explain the collision to readers (owner decision 2026-10-25: assume the reader knows Blocknet).

## Main site and blog boundaries

The homepage `/` owns **Seine download / Blocknet miner software**: supported operating
systems, release downloads, a short setup summary and measured performance highlights.
`/#download`, `/#start` and `/#performance` are sections of that same canonical page,
not separate landing pages. The guides own detailed installation, wallet setup,
hardware sizing and tuning. Homepage links route readers to those existing owners
in their selected language; do not create parallel download or tuning articles.

## Current ownership

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| how to mine blocknet | `/blog/how-to-mine-blocknet/` | Get a newcomer from zero to accepted shares on any OS, and set expectations for payouts and hashrate | blocknet mining guide, blocknet miner, mine Blocknet BNT, bntpool setup, Blocknet Argon2id miner, 如何挖 Blocknet |
| what is blocknet | `/blog/what-is-blocknet/` | Explain what Blocknet is and does for someone new, then route to names, privacy and mining | Blocknet privacy coin, Blocknet cryptocurrency, Blocknet fair launch, Blocknet Faraday upgrade, Blocknet 是什么 |
| blocknet privacy | `/blog/blocknet-privacy-features/` | Explain each layer of Blocknet's mandatory privacy and what it means when you pay | blocknet ring signatures, blocknet stealth address, blocknet ring size, Blocknet 隐私 |
| blocknet id | `/blog/blocknet-id-pay-by-name/` | Claim a Blocknet ID shortname and get paid to `@name` (wallet, payment links, pool payouts) | blocknet.id, blocknet shortname, pay by name blocknet, mine to @name, Blocknet ID 短名称 |
| argon2id proof of work | `/blog/argon2id-proof-of-work-explained/` | Explain how Blocknet's Argon2id PoW works and why RAM and bandwidth decide hashrate | argon2id mining, argon2id parameters, memory-hard proof of work, blocknet 2 GB per thread, Argon2id 工作量证明 |
| best hardware for blocknet mining | `/blog/blocknet-mining-hardware-hashrate/` | Pick or size a mining machine: fastest hardware, threads per GB of RAM, expected H/s, CPU and GPU together | blocknet hashrate, blocknet mining RAM per thread, best CPU for Blocknet, Argon2id mining hardware, 挖 Blocknet 用什么硬件 |
| mine blocknet on mac | `/blog/mine-blocknet-on-mac/` | Set up and size Blocknet mining on an Apple Silicon Mac | blocknet apple silicon, blocknet m4 max hashrate, mine blocknet macbook, seine macos, 在 Mac 上挖 Blocknet |
| blocknet memo | `/blog/blocknet-encrypted-memos/` | Add an encrypted memo (invoice, order number, note) to a Blocknet payment, know who can read it, and find received memos | blocknet encrypted memo, blocknet payment memo, blocknet send memo, blocknet memo length, Blocknet 加密备注 / 加密備註 |
| blocknet payment link | `/blog/blocknet-payment-links/` | Write a `blocknet://` or bntpay.com link that requests an amount (with memo and `$name`) and know what pasting it does | bntpay link, blocknet uri, blocknet://, request BNT payment, blocknet invoice link, Blocknet 付款链接 / 付款連結 |
| huge pages blocknet mining | `/blog/huge-pages-blocknet-mining/` | Reserve huge pages (Linux/WSL 2 MiB and 1 GiB) or Windows large pages for seine: why they help Argon2id, pages per thread, exact commands, page modes | blocknet hugepages, seine hugepages, vm.nr_hugepages mining, 1GB huge pages argon2id, windows large pages mining, lock pages in memory seine, Blocknet 大页内存 / 大分頁 |
| mine blocknet on servers | `/blog/mine-blocknet-on-servers/` | Run seine on many-core servers and rigs: NUMA/L3 placement and its measured gains, headless runs, `--service`, the control API, live events and Prometheus | blocknet mining server, blocknet NUMA, EPYC blocknet mining, seine headless, seine control API, seine Prometheus metrics, 在服务器上挖 Blocknet / 在伺服器上挖 Blocknet |
| get a blocknet wallet for mining | `/blog/blocknet-wallet-for-mining/` | Create an official Blocknet wallet, back up the seed, get the address to mine to and watch pool payouts arrive | blocknet wallet, blocknet address, blocknet recovery seed, blocknet desktop wallet, blocknet cli wallet, 获取 Blocknet 钱包地址 / 取得 Blocknet 錢包地址 |
| seine dashboard | `/blog/seine-dashboard-explained/` | Read seine's terminal dashboard: every panel and label, live auto-tuning in the log, keyboard thread controls | seine hashrate current vs average, seine accepted rejected shares, seine change threads while mining, seine tui, seine --ui plain, seine 仪表盘 / 儀表板 |
| what is a privacy coin | `/blog/what-is-a-privacy-coin/` | Explain what a privacy coin is for any coin: what a transparent chain reveals, how privacy coins hide sender, receiver, amount and network origin, and why privacy by default matters, with Blocknet as the worked example | privacy coin meaning, privacy cryptocurrency, how privacy coins work, private by default crypto, privacy coin vs bitcoin, 什么是隐私币 / 什麼是隱私幣 |
| ring signatures explained | `/blog/ring-signatures-explained/` | Explain how ring signatures work for any coin (signer hidden among public keys, key images, LSAG to CLSAG, ring size), with Blocknet's ring of 16 as the example | what is a ring signature, how do ring signatures work, linkable ring signature, key image, CLSAG ring signature, ring size, 环签名 / 環簽章 |
| stealth addresses explained | `/blog/stealth-addresses-explained/` | Explain how stealth (one-time) addresses work for any coin: view and spend keys, the sender/receiver math, view-only wallets and wallet scanning, with Blocknet as the example | stealth address, one-time address, what is a view key, private view key vs spend key, view-only wallet, how wallets scan for payments, 隐身地址 / 隱身地址, 查看密钥 / 檢視金鑰 |
| bulletproofs explained | `/blog/bulletproofs-explained/` | Explain Pedersen commitments and Bulletproofs range proofs for anyone, then show how Blocknet verifies hidden amounts | pedersen commitment, confidential transactions, range proof, bulletproofs size, hidden transaction amounts, Bulletproofs 详解 / 詳解, Pedersen 承诺 / 承諾, 范围证明 / 範圍證明 |
| dandelion++ explained | `/blog/dandelion-plus-plus-explained/` | Explain Dandelion++ stem and fluff relay for any coin, why it hides the sending node, what the 2018 paper changed, and Blocknet's relay settings | dandelion++, dandelion protocol crypto, stem and fluff, transaction relay privacy, blocknet dandelion++, Dandelion++ 交易中继 / 交易中繼 |
| proof of work vs proof of stake | `/blog/proof-of-work-vs-proof-of-stake/` | Explain neutrally how PoW and PoS choose blocks, stay secure and issue coins, and why Blocknet uses memory-hard PoW | pow vs pos, difference between proof of work and proof of stake, proof of stake explained, is blocknet proof of work, 51% attack, 工作量证明和权益证明的区别 / 工作量證明與權益證明的差異 |
| how crypto mining works | `/blog/how-crypto-mining-works/` | Explain proof-of-work mining in plain words (blocks, hashes, nonce, difficulty, rewards, pools and shares) with Blocknet as the worked example, then route to the mining guide | how does cryptocurrency mining work, what is crypto mining, mining difficulty explained, what is a mining pool share, block reward explained, 加密货币挖矿原理 / 加密貨幣挖礦原理 |
| cpu mining 2026 | `/blog/cpu-mining-2026/` | Explain CPU mining in 2026: why memory-hard coins favor ordinary computers, what to check in a CPU coin, what makes a CPU fast, and how to start with seine | what to mine with a cpu, cpu mineable coins, memory-hard coin cpu, is cpu mining dead, CPU 挖矿 / CPU 挖礦, 用 CPU 挖什么币 |
| mine crypto on old pc or laptop | `/blog/mine-crypto-on-old-pc-or-laptop/` | Decide whether a spare old desktop or laptop can mine, size threads to its RAM, keep it cool, and start safely with seine on bntpool.com | mining on an old laptop, mine crypto on laptop, old computer crypto mining, laptop mining 8GB RAM, seine efficiency profile, 用旧电脑挖矿 / 用舊電腦挖礦, 笔记本电脑挖矿 / 筆記型電腦挖礦 |
| seed phrase explained | `/blog/seed-phrase-explained/` | Explain what a wallet seed (recovery) phrase is, how it becomes keys, how to store it and why never to share it, with Blocknet's 12-word seed as the example | what is a seed phrase, recovery phrase, mnemonic phrase, 12-word seed, how to store seed phrase, BIP39 explained, blocknet recovery seed, 助记词是什么 / 助記詞是什麼 |

| mine blocknet on windows | `/blog/mine-blocknet-on-windows/` | Install and verify the Windows ZIP, run native PowerShell commands, complete first-run prompts and confirm accepted shares | Windows Blocknet miner, seine Windows setup, Blocknet NVIDIA Windows, 在 Windows 上挖 Blocknet |
| blocknet gpu mining; blocknet NVIDIA mining; mine blocknet RTX 5090 | `/blog/mine-blocknet-nvidia-gpu/` | Prepare the NVIDIA runtime, choose GPU-only or CPU-plus-GPU mining, verify accepted GPU shares, and compare the measured RTX 5090 modes | NVIDIA Blocknet setup, Blocknet GPU VRAM, CPU and GPU mining together |

| windows defender crypto miner; antivirus blocks miner; verify seine download | `/blog/antivirus-flags-crypto-miner/` | Identify a blocked-download warning, verify the exact official Windows archive and gather evidence for an unresolved detection | SmartScreen miner warning, seine SHA-256, miner quarantine |

## Boundaries

| Broad owner | Narrow owner | Boundary |
|---|---|---|
| `/blog/how-to-mine-blocknet/` | `/blog/blocknet-mining-hardware-hashrate/` | The guide shows one best-per-generation table and links out; the hardware post owns buying advice and full per-chip results. |
| `/blog/what-is-blocknet/` | `/blog/blocknet-privacy-features/`, `/blog/blocknet-id-pay-by-name/` | The overview summarizes privacy and names in a paragraph each and links out; the narrow posts own the mechanics. |
| `/blog/blocknet-mining-hardware-hashrate/` | `/blog/mine-blocknet-on-mac/` | The hardware post has one Mac row; the Mac post owns macOS setup and thread sizing by Mac memory. |
| `/blog/argon2id-proof-of-work-explained/` | `/blog/blocknet-mining-hardware-hashrate/` | The explainer owns why memory decides hashrate; the hardware post owns which machine to buy or use. |
| `/blog/blocknet-privacy-features/` | `/blog/blocknet-encrypted-memos/` | The privacy post explains in one section who can read a memo and why it is padded; the memos post owns adding, sending and reading memos. |
| `/blog/blocknet-id-pay-by-name/` | `/blog/blocknet-payment-links/` | The Blocknet ID post shows the two link forms with a name in one section; the payment-links post owns the full link format, encoding and the paste-to-confirm flow. |
| `/blog/blocknet-payment-links/` | `/blog/blocknet-encrypted-memos/` | The payment-links post says a link can carry a memo; the memos post owns memo encryption, padding and the `send` memo argument. |
| `/blog/how-to-mine-blocknet/` | `/blog/blocknet-wallet-for-mining/`, `/blog/seine-dashboard-explained/` | The guide has one bullet on getting an address and one line on the dashboard; the narrow posts own the wallet walkthrough and the panel-by-panel dashboard tour. |
| `/blog/blocknet-wallet-for-mining/` | `/blog/blocknet-id-pay-by-name/` | The wallet post mentions shortnames in one sentence; the Blocknet ID post owns names. |
| `/blog/argon2id-proof-of-work-explained/`, `/blog/blocknet-mining-hardware-hashrate/`, `/blog/how-to-mine-blocknet/` | `/blog/huge-pages-blocknet-mining/` | The broader posts keep a one-line huge-pages tip and link out; the huge-pages post owns sizing, commands and page modes. |
| `/blog/blocknet-mining-hardware-hashrate/` | `/blog/mine-blocknet-on-servers/` | The hardware post owns which machine to buy; the servers post owns running seine on big machines and rigs (placement, headless, control API). |
| `/blog/mine-blocknet-on-servers/` | `/blog/huge-pages-blocknet-mining/` | The servers post notes that placement and huge pages stack and that pools must be node-local; the huge-pages post owns reserving pages. |
| `/blog/what-is-a-privacy-coin/` | `/blog/blocknet-privacy-features/` | The privacy-coin explainer owns the coin-agnostic concept and gives Blocknet one bulleted summary; the privacy post owns Blocknet's layers in depth and "blocknet privacy". |
| `/blog/what-is-blocknet/` | `/blog/what-is-a-privacy-coin/` | The overview answers "is Blocknet a privacy coin?" in a paragraph and links out; the explainer owns what a privacy coin is in general. |
| `/blog/what-is-a-privacy-coin/` | `/blog/ring-signatures-explained/`, `/blog/stealth-addresses-explained/`, `/blog/bulletproofs-explained/`, `/blog/dandelion-plus-plus-explained/` | The privacy-coin explainer gives each technique one paragraph and links out; each explainer owns its mechanism. |
| `/blog/blocknet-privacy-features/` | `/blog/ring-signatures-explained/` | The privacy post keeps one section on Blocknet's ring of 16 and "blocknet ring signatures"; the explainer owns how ring signatures, key images and CLSAG work for any coin. |
| `/blog/blocknet-privacy-features/` | `/blog/stealth-addresses-explained/` | The privacy post keeps "blocknet stealth address" in two paragraphs; the explainer owns the key math, view keys, view-only wallets and scanning. |
| `/blog/blocknet-privacy-features/` | `/blog/bulletproofs-explained/` | The privacy post keeps one section on hidden amounts; the explainer owns Pedersen commitments, range proofs and the Bulletproofs construction. |
| `/blog/blocknet-privacy-features/` | `/blog/dandelion-plus-plus-explained/` | The privacy post keeps a short Dandelion++ section; the explainer owns stem and fluff relay, the 2018 paper and Blocknet's full relay settings. |
| `/blog/stealth-addresses-explained/` | `/blog/blocknet-wallet-for-mining/`, `/blog/blocknet-id-pay-by-name/` | The explainer covers `viewkeys` and seed recovery in a paragraph each and mentions names; the wallet post owns wallet setup and seed backup, the Blocknet ID post owns names. |
| `/blog/proof-of-work-vs-proof-of-stake/` | `/blog/argon2id-proof-of-work-explained/`, `/blog/how-crypto-mining-works/` | The comparison summarizes PoW in one section with Blocknet's four consensus facts; the Argon2id explainer owns the hash internals and memory arithmetic, and the mining explainer owns the general mining walkthrough. |
| `/blog/how-crypto-mining-works/` | `/blog/how-to-mine-blocknet/`, `/blog/argon2id-proof-of-work-explained/` | The explainer owns the coin-agnostic concepts (blocks, nonce, difficulty, rewards, pools and shares) and ends with a three-step summary; the guide owns the setup steps and the Argon2id post owns how the hash works. |
| `/blog/cpu-mining-2026/` | `/blog/blocknet-mining-hardware-hashrate/`, `/blog/mine-crypto-on-old-pc-or-laptop/` | The CPU post owns "what to mine with a CPU" and keeps one best-per-generation table and a RAM rule of thumb; the hardware post owns buying advice and full per-chip results, and the old-PC post owns small-RAM sizing, cooling and power. |
| `/blog/blocknet-mining-hardware-hashrate/` | `/blog/mine-crypto-on-old-pc-or-laptop/` | The hardware post's RAM table starts at 16 GB and shows hashrates; the old-PC post owns 4-12 GB machines, laptop cooling, the efficiency profile and electricity arithmetic, with no hashrate table. |
| `/blog/seed-phrase-explained/` | `/blog/blocknet-wallet-for-mining/` | The explainer owns BIP39, seed-to-key derivation, storage habits and scams, and summarizes view/restore in one section; the wallet post owns creating the wallet, the `seed`/`import` walkthrough and finding the address. |

bntpool.com's blog (blocknet-pool repo, `frontend/blog/`) owns pool-side jobs (joining the pool,
PPLNS payouts, miner stats, the reward schedule, the fair launch). Don't target those here.

The Windows guide owns the native Windows ZIP/checksum/PowerShell walkthrough. The general mining guide remains the cross-platform overview; the huge-pages guide owns detailed page setup.

The NVIDIA guide owns card selection, NVIDIA runtime diagnosis, accepted GPU-share verification and the dated RTX 5090 comparison. The Windows guide owns ZIP/checksum/PowerShell setup, the dashboard guide owns the panel tour, and bntpool.com owns pool-credit tracking. No RTX 4090 performance or other unmeasured card result is claimed.

The hardware comparison guide also presents the dated RTX 5090 results with the original method and evidence, as part of its per-chip coverage. Its shared measurement section has 8.2% wording overlap with the NVIDIA guide; runtime setup, commands and troubleshooting remain in the NVIDIA guide, linked from the hardware article.

The download-verification guide owns warning identification, archive integrity checks and detection reports. The Windows guide retains the normal installation flow and its brief checksum step; the NVIDIA guide owns runtime and device setup. Neither file integrity nor the software category is presented as an antivirus verdict. Both setup guides link to the new troubleshooting owner.
