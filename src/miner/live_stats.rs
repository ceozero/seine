//! Live mining statistics for the control API (`GET /v1/miner/stats`).
//!
//! The mining loops feed this module the same per-round view they give the
//! TUI, so rates and share counts are available in every UI mode. Recording is
//! off until the control API enables it.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::Serialize;

use super::backend_display_names;
use super::hashrate_tracker::HashrateTracker;
use super::mining_tui::{
    current_hashrate_window_overrides, should_zero_current_hashrate, RoundUiView,
};
use super::stats::Stats;

const RECORD_INTERVAL: Duration = Duration::from_secs(1);
/// Current rates read as zero when the mining loop has not reported for this
/// long (for example while reconnecting to the pool).
const STALE_AFTER: Duration = Duration::from_secs(30);

static ENABLED: AtomicBool = AtomicBool::new(false);
static STATE: Mutex<Option<LiveState>> = Mutex::new(None);

#[derive(Debug, Clone, Serialize, PartialEq)]
pub(crate) struct LiveDeviceStats {
    /// Backend instance label, for example `nvidia#1` or `cpu#1`.
    pub label: String,
    /// Backend kind: `cpu`, `nvidia`, `amd` or `metal`.
    pub kind: String,
    /// GPU index for GPU backends.
    pub device_index: Option<u32>,
    /// PCI address (`dddd:bb:dd.f`) for GPU backends when known.
    pub pci_address: Option<String>,
    pub lanes: usize,
    pub hashrate_hps: f64,
    pub average_hashrate_hps: f64,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub(crate) struct LiveMiningStats {
    /// Mining state, for example `working`, `pool-login-rejected` or `wallet-required`.
    pub state: String,
    /// Seconds since this mining session started.
    pub uptime_secs: f64,
    pub updated_at_unix_ms: u64,
    pub hashrate_hps: f64,
    pub average_hashrate_hps: f64,
    pub total_hashes: u64,
    /// Shares (pool mode) or blocks (daemon mode) submitted.
    pub submitted: u64,
    pub accepted: u64,
    /// Rejected or stale shares/blocks.
    pub rejected: u64,
    pub devices: Vec<LiveDeviceStats>,
}

struct LiveState {
    session_started_at: Instant,
    last_record: Option<Instant>,
    last_update: Instant,
    tracker: HashrateTracker,
    stats: LiveMiningStats,
}

/// Turns recording on; called once when the control API starts.
pub(crate) fn enable() {
    ENABLED.store(true, Ordering::Release);
}

fn enabled() -> bool {
    ENABLED.load(Ordering::Acquire)
}

fn unix_ms_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_millis().min(u128::from(u64::MAX)) as u64)
        .unwrap_or(0)
}

/// States in which the miner is not hashing, so current rates read as zero.
fn is_idle_state(state_label: &str) -> bool {
    should_zero_current_hashrate(state_label)
        || matches!(
            state_label,
            "pool-connecting" | "pool-disconnected" | "pool-login-rejected"
        )
}

impl LiveState {
    fn new(session_started_at: Instant) -> Self {
        Self {
            session_started_at,
            last_record: None,
            last_update: Instant::now(),
            tracker: HashrateTracker::new(),
            stats: LiveMiningStats {
                state: "starting".to_string(),
                uptime_secs: 0.0,
                updated_at_unix_ms: unix_ms_now(),
                hashrate_hps: 0.0,
                average_hashrate_hps: 0.0,
                total_hashes: 0,
                submitted: 0,
                accepted: 0,
                rejected: 0,
                devices: Vec::new(),
            },
        }
    }

    fn record(&mut self, stats: &Stats, view: &RoundUiView<'_>) {
        if self.last_record.is_some_and(|last| {
            last.elapsed() < RECORD_INTERVAL && self.stats.state == view.state_label
        }) {
            return;
        }

        let snapshot = stats.snapshot();
        let idle = is_idle_state(view.state_label);
        self.tracker.set_paused(idle);
        self.tracker
            .record(snapshot.hashes, view.round_start, view.round_backend_hashes);
        let windows = current_hashrate_window_overrides(view.backends);
        let rates = self.tracker.rates_with_current_windows(&windows);
        let names = backend_display_names(view.backends);

        let devices = view
            .backends
            .iter()
            .map(|slot| LiveDeviceStats {
                label: names
                    .get(&slot.id)
                    .cloned()
                    .unwrap_or_else(|| format!("{}#{}", slot.backend.name(), slot.id)),
                kind: slot.backend.name().to_string(),
                device_index: slot.backend.device_index(),
                pci_address: slot.backend.pci_address(),
                lanes: slot.backend.enabled_lanes(),
                hashrate_hps: if idle {
                    0.0
                } else {
                    rates
                        .current_per_device
                        .get(&slot.id)
                        .copied()
                        .unwrap_or(0.0)
                },
                average_hashrate_hps: rates
                    .average_per_device
                    .get(&slot.id)
                    .copied()
                    .unwrap_or(0.0),
            })
            .collect();

        self.stats = LiveMiningStats {
            state: view.state_label.to_string(),
            uptime_secs: snapshot.elapsed_secs,
            updated_at_unix_ms: unix_ms_now(),
            hashrate_hps: if idle { 0.0 } else { rates.current_total },
            average_hashrate_hps: rates.average_total,
            total_hashes: snapshot.hashes,
            submitted: snapshot.submitted,
            accepted: snapshot.accepted,
            rejected: snapshot.stale_shares,
            devices,
        };
        let now = Instant::now();
        self.last_record = Some(now);
        self.last_update = now;
    }

    fn set_state(&mut self, state_label: &str) {
        let idle = is_idle_state(state_label);
        self.tracker.set_paused(idle);
        self.stats.state = state_label.to_string();
        if idle {
            self.stats.hashrate_hps = 0.0;
            for device in &mut self.stats.devices {
                device.hashrate_hps = 0.0;
            }
        }
        self.stats.updated_at_unix_ms = unix_ms_now();
    }

    fn snapshot(&self) -> LiveMiningStats {
        let mut stats = self.stats.clone();
        stats.uptime_secs = self.session_started_at.elapsed().as_secs_f64();
        if self.last_update.elapsed() >= STALE_AFTER {
            stats.hashrate_hps = 0.0;
            for device in &mut stats.devices {
                device.hashrate_hps = 0.0;
            }
        }
        stats
    }
}

/// Records one round sample. Cheap to call on every hash poll: samples are
/// taken at most once per second.
pub(super) fn record(stats: &Stats, view: &RoundUiView<'_>) {
    if !enabled() {
        return;
    }
    let Ok(mut guard) = STATE.lock() else {
        return;
    };
    let state = guard.get_or_insert_with(|| LiveState::new(stats.started_at()));
    if state.session_started_at != stats.started_at() {
        *state = LiveState::new(stats.started_at());
    }
    state.record(stats, view);
}

/// Records a mining state change that has no round view (for example a pool
/// disconnect). Idle states read as zero current hashrate.
pub(super) fn set_state(state_label: &str) {
    if !enabled() {
        return;
    }
    if let Ok(mut guard) = STATE.lock() {
        if let Some(state) = guard.as_mut() {
            state.set_state(state_label);
        }
    }
}

/// Clears the published stats, for example when the miner stops.
pub(crate) fn clear() {
    if let Ok(mut guard) = STATE.lock() {
        *guard = None;
    }
}

/// Latest stats, or `None` before the first sample of a session. Current
/// rates read as zero once samples stop arriving.
pub(crate) fn snapshot() -> Option<LiveMiningStats> {
    let guard = STATE.lock().ok()?;
    guard.as_ref().map(LiveState::snapshot)
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::sync::Arc;

    use anyhow::Result;
    use crossbeam_channel::Sender;

    use super::*;
    use crate::backend::{BackendEvent, BackendInstanceId, PowBackend, WorkAssignment};
    use crate::miner::BackendSlot;

    struct FakeGpu {
        index: u32,
    }

    impl PowBackend for FakeGpu {
        fn name(&self) -> &'static str {
            "nvidia"
        }

        fn lanes(&self) -> usize {
            3
        }

        fn device_index(&self) -> Option<u32> {
            Some(self.index)
        }

        fn pci_address(&self) -> Option<String> {
            Some(format!("0000:{:02x}:00.0", self.index + 1))
        }

        fn set_instance_id(&self, _id: BackendInstanceId) {}

        fn set_event_sink(&self, _sink: Sender<BackendEvent>) {}

        fn start(&self) -> Result<()> {
            Ok(())
        }

        fn stop(&self) {}

        fn assign_work(&self, _work: WorkAssignment) -> Result<()> {
            Ok(())
        }

        fn cancel_work(&self) -> Result<()> {
            Ok(())
        }

        fn fence(&self) -> Result<()> {
            Ok(())
        }
    }

    fn slot(id: BackendInstanceId, index: u32) -> BackendSlot {
        let backend: Arc<dyn PowBackend> = Arc::new(FakeGpu { index });
        BackendSlot {
            id,
            capabilities: backend.capabilities(),
            backend,
            lanes: 3,
            runtime_policy: crate::miner::BackendRuntimePolicy::default(),
        }
    }

    fn view<'a>(
        backends: &'a [BackendSlot],
        hashes: &'a BTreeMap<BackendInstanceId, u64>,
        round_start: Instant,
        state_label: &'a str,
    ) -> RoundUiView<'a> {
        RoundUiView {
            backends,
            round_backend_hashes: hashes,
            round_start,
            height: "100",
            network_hashrate: "-",
            epoch: 1,
            state_label,
        }
    }

    #[test]
    fn records_devices_shares_and_idle_states() {
        let stats = Stats::new();
        let backends = vec![slot(7, 0), slot(9, 1)];
        let round_start = Instant::now();
        let mut state = LiveState::new(stats.started_at());

        let empty = BTreeMap::new();
        state.record(&stats, &view(&backends, &empty, round_start, "working"));
        stats.add_hashes(60);
        stats.bump_submitted();
        stats.bump_submitted();
        stats.bump_accepted();
        stats.bump_stale_shares();
        // Backdate the first sample so the next one spans a full rate window.
        state.last_record = Some(Instant::now() - RECORD_INTERVAL);
        state.tracker.backdate_samples(Duration::from_secs(3));
        let hashes = BTreeMap::from([(7, 40), (9, 20)]);
        state.record(&stats, &view(&backends, &hashes, round_start, "working"));

        let live = state.snapshot();
        assert_eq!(live.state, "working");
        assert_eq!(live.total_hashes, 60);
        assert_eq!((live.submitted, live.accepted, live.rejected), (2, 1, 1));
        assert!(live.hashrate_hps > 0.0, "{live:?}");
        let labels: Vec<_> = live.devices.iter().map(|d| d.label.as_str()).collect();
        assert_eq!(labels, ["nvidia#1", "nvidia#2"]);
        assert_eq!(live.devices[1].device_index, Some(1));
        assert_eq!(live.devices[1].pci_address.as_deref(), Some("0000:02:00.0"));
        assert_eq!(live.devices[0].lanes, 3);
        assert!(live.devices[0].hashrate_hps > live.devices[1].hashrate_hps);

        state.set_state("pool-disconnected");
        let live = state.snapshot();
        assert_eq!(live.state, "pool-disconnected");
        assert_eq!(live.hashrate_hps, 0.0);
        assert!(live.devices.iter().all(|d| d.hashrate_hps == 0.0));
        assert_eq!(live.accepted, 1, "counters survive idle states");

        state.last_update = Instant::now() - STALE_AFTER;
        state.stats.hashrate_hps = 5.0;
        assert_eq!(
            state.snapshot().hashrate_hps,
            0.0,
            "stale samples read as idle"
        );
    }
}
