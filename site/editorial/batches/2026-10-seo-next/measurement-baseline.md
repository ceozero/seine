# First audience-data check

Checked **October 25, 2026, 5:30 PM EDT**, immediately after the rollout.

## Evidence

| Source | Observation | What it supports |
|---|---|---|
| Search Console, `sc-domain:seineminer.com`, Performance, three months | “Processing data, please check again in a day or so”; query table has no data | Query impressions, clicks, CTR and positions are unavailable, not measured zeros |
| Search Console, `https://bntpool.com/`, Performance, three months | Same processing message and empty query table | No pool query/page prioritization is possible yet |
| Private `/api/admin/site-metrics` | Collector ready; exactly two saved counters | Collection is operational, but this is not audience evidence |

The two saved counters are the already documented QA events from the preceding
ship: one English pool-setup click from `track-your-miner-on-bntpool` and one
English download click from `mine-blocknet-on-windows`. After excluding them,
there are **zero recorded non-test events**. This does not establish zero visitors:
the collector is new and respects DNT/GPC and browser blocking. Do not compute a
conversion rate from this baseline or treat click counts as completed downloads.

## Decision

No article is promoted or retargeted on the basis of these empty reports. Existing
keyword ownership stays in force. The NVIDIA guide remains the next candidate
from the earlier search-landscape research, not a newly observed traffic winner.
It still needs verified per-card and CPU-plus-GPU measurements; none were collected
in this check. RAM sizing and zero pool hashrate already have existing owners.

## Next review

- Check report availability on October 26, following Search Console's message.
  No reminder or recurring task was created.
- Once data is available, record query, page, language/country, device, date range,
  impressions, clicks, CTR and position. Preserve the actual coverage period.
- Improve existing owners when their relevant queries show impressions but weak
  clicks. Compare similar devices and positions before interpreting CTR.
- Combine those findings with article views and download/setup click intent for
  the same period. Exclude the two October 25 QA clicks, keep sites/languages
  separate, and avoid ranking pages from tiny samples.
- Commission a new article only for a distinct reader task with enough supporting
  evidence. Use the keyword map to route improvements to the current owner.
- Treat the first populated report as a baseline; assess rollout trends after
  four to eight weeks, as specified in the original Search Console audit.

The check was read-only for production. No content was published, services
restarted, benchmarks launched, or shared browser settings changed. The task's
Search Console tab was closed afterward. This file records the baseline only.
