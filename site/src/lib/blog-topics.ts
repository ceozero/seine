// Every published article has one topic; translations share the source slug.
export const TOPICS = [
  {
    "id": "getting-started",
    "key": "topicGettingStarted"
  },
  {
    "id": "hardware",
    "key": "topicHardware"
  },
  {
    "id": "troubleshooting",
    "key": "topicTroubleshooting"
  },
  {
    "id": "rewards",
    "key": "topicRewards"
  },
  {
    "id": "blocknet",
    "key": "topicBlocknet"
  }
] as const;
const groups: Record<string, readonly string[]> = {
  "getting-started": [
    "how-to-mine-blocknet",
    "mine-blocknet-on-windows",
    "mine-blocknet-on-mac",
    "blocknet-wallet-for-mining",
    "how-crypto-mining-works"
  ],
  "hardware": [
    "mine-blocknet-nvidia-gpu",
    "mine-blocknet-on-servers",
    "blocknet-mining-hardware-hashrate",
    "mine-crypto-on-old-pc-or-laptop",
    "huge-pages-blocknet-mining",
    "cpu-mining-2026",
    "argon2id-proof-of-work-explained"
  ],
  "troubleshooting": [
    "antivirus-flags-crypto-miner",
    "seine-dashboard-explained"
  ],
  "blocknet": [
    "dandelion-plus-plus-explained",
    "proof-of-work-vs-proof-of-stake",
    "blocknet-payment-links",
    "what-is-blocknet",
    "seed-phrase-explained",
    "blocknet-privacy-features",
    "what-is-a-privacy-coin",
    "bulletproofs-explained",
    "blocknet-encrypted-memos",
    "stealth-addresses-explained",
    "blocknet-id-pay-by-name",
    "ring-signatures-explained"
  ]
};
export function topicFor(slug: string) {
    const matches = TOPICS.filter(t => groups[t.id]?.includes(slug));
    if (matches.length !== 1) throw new Error(`Assign exactly one blog topic to ${slug}`);
    return matches[0];
}
