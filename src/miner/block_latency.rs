//! Process-wide latency histograms for seine's side of the block path: a
//! backend finding a nonce, the submit reaching the pool or daemon, and a new
//! job or template reaching the backends. Rendered on the control API's
//! `/metrics` as `seine_block_path_latency_millis{lane=...}`, with the same
//! bucket bounds as blocknet-pool so both sides compare directly.

use std::collections::BTreeMap;
use std::sync::Mutex;
use std::time::Duration;

/// Inclusive bucket upper bounds in milliseconds (blocknet-pool's
/// `LATENCY_BUCKET_BOUNDS_MILLIS`).
const BUCKET_BOUNDS_MILLIS: [u64; 29] = [
    1, 2, 5, 10, 25, 50, 100, 250, 500, 750, 1_000, 1_250, 1_500, 1_750, 2_000, 2_250, 2_500,
    2_750, 3_000, 3_500, 4_000, 5_000, 7_500, 10_000, 15_000, 30_000, 60_000, 120_000, 300_000,
];

/// Pool job line decoded → the mining loop starts switching to it.
pub(crate) const POOL_JOB_RECEIVED_TO_HANDLED: &str = "pool_job_received_to_handled";
/// Cancelling the previous job's backend work.
pub(crate) const POOL_JOB_CANCEL: &str = "pool_job_cancel";
/// Assigning the new job to backends.
pub(crate) const POOL_JOB_ASSIGN: &str = "pool_job_assign";
/// Pool job line decoded → backends assigned the new job.
pub(crate) const POOL_JOB_SWITCH: &str = "pool_job_switch";
/// Backend found a nonce → the mining loop handled the solution.
pub(crate) const POOL_FOUND_TO_LOOP: &str = "pool_found_to_loop";
/// Backend found a nonce → the submit was queued to the pool socket.
pub(crate) const POOL_FOUND_TO_SEND: &str = "pool_found_to_send";
/// Submit queued → pool acknowledgement.
pub(crate) const POOL_SUBMIT_TO_ACK: &str = "pool_submit_to_ack";
/// blocktemplate round trip (solo mining).
pub(crate) const SOLO_TEMPLATE_FETCH: &str = "solo_template_fetch";
/// Daemon new-block event → a template building on it is prepared for the
/// backends (solo mining).
pub(crate) const SOLO_TIP_TO_TEMPLATE: &str = "solo_tip_to_template";
/// Backend found a block → submitblock sent (solo mining).
pub(crate) const SOLO_FOUND_TO_SUBMIT: &str = "solo_found_to_submit";
/// submitblock round trip (solo mining).
pub(crate) const SOLO_SUBMIT_RTT: &str = "solo_submit_rtt";

struct Histogram {
    counts: [u64; BUCKET_BOUNDS_MILLIS.len() + 1],
    sum_micros: u64,
}

static LANES: Mutex<BTreeMap<&'static str, Histogram>> = Mutex::new(BTreeMap::new());

pub(crate) fn record(lane: &'static str, elapsed: Duration) {
    let micros = elapsed.as_micros().min(u64::MAX as u128) as u64;
    let idx = BUCKET_BOUNDS_MILLIS.partition_point(|bound| bound.saturating_mul(1_000) < micros);
    let mut lanes = LANES.lock().unwrap_or_else(|err| err.into_inner());
    let histogram = lanes.entry(lane).or_insert(Histogram {
        counts: [0; BUCKET_BOUNDS_MILLIS.len() + 1],
        sum_micros: 0,
    });
    histogram.counts[idx] = histogram.counts[idx].saturating_add(1);
    histogram.sum_micros = histogram.sum_micros.saturating_add(micros);
}

/// Appends the Prometheus histogram series for every recorded lane.
pub(crate) fn render_prometheus(out: &mut String) {
    const NAME: &str = "seine_block_path_latency_millis";
    let lanes = LANES.lock().unwrap_or_else(|err| err.into_inner());
    if lanes.is_empty() {
        return;
    }
    out.push_str(&format!("# TYPE {NAME} histogram\n"));
    for (lane, histogram) in lanes.iter() {
        let mut cumulative = 0u64;
        for (idx, count) in histogram.counts.iter().enumerate() {
            cumulative = cumulative.saturating_add(*count);
            let le = BUCKET_BOUNDS_MILLIS
                .get(idx)
                .map(u64::to_string)
                .unwrap_or_else(|| "+Inf".to_string());
            out.push_str(&format!(
                "{NAME}_bucket{{lane=\"{lane}\",le=\"{le}\"}} {cumulative}\n"
            ));
        }
        out.push_str(&format!(
            "{NAME}_sum{{lane=\"{lane}\"}} {}\n",
            histogram.sum_micros as f64 / 1_000.0
        ));
        out.push_str(&format!("{NAME}_count{{lane=\"{lane}\"}} {cumulative}\n"));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_render_as_cumulative_prometheus_buckets() {
        const LANE: &str = "test_lane_render";
        record(LANE, Duration::from_micros(700));
        record(LANE, Duration::from_millis(4));
        let mut out = String::new();
        render_prometheus(&mut out);
        for line in [
            "seine_block_path_latency_millis_bucket{lane=\"test_lane_render\",le=\"1\"} 1\n",
            "seine_block_path_latency_millis_bucket{lane=\"test_lane_render\",le=\"5\"} 2\n",
            "seine_block_path_latency_millis_bucket{lane=\"test_lane_render\",le=\"+Inf\"} 2\n",
            "seine_block_path_latency_millis_sum{lane=\"test_lane_render\"} 4.7\n",
            "seine_block_path_latency_millis_count{lane=\"test_lane_render\"} 2\n",
        ] {
            assert!(out.contains(line), "missing {line:?} in\n{out}");
        }
    }
}
