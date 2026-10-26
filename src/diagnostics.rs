//! Bounded failure counters. Free-form messages never enter the upload state.
use crate::config::{BackendKind, Config, CpuAffinityMode, MiningMode};
use seine_telemetry::{
    DiagnosticCode, DiagnosticEvent, DiagnosticKind, DiagnosticOperation, Diagnostics,
    FailureDetail, FailureReason, PreviousRun, Report, RunPhase, MAX_BODY_BYTES,
};
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    panic::Location,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        Arc, Mutex, Once, Weak,
    },
    time::{Duration, Instant, SystemTime},
};

static ACTIVE: Mutex<Option<Weak<Recorder>>> = Mutex::new(None);
static PANIC_HOOK: Once = Once::new();
type Key = (
    DiagnosticCode,
    DiagnosticKind,
    String,
    u32,
    Option<String>,
    Option<FailureDetail>,
    RunPhase,
);

pub(crate) struct Recorder {
    started: Instant,
    context: Diagnostics,
    events: Mutex<BTreeMap<Key, DiagnosticEvent>>,
    dropped: AtomicU64,
    failed: AtomicBool,
    previous_unclean: AtomicBool,
    phase: Mutex<RunPhase>,
    previous_run: Mutex<Option<PreviousRun>>,
}

pub(crate) struct Guard(pub Arc<Recorder>);
impl Drop for Guard {
    fn drop(&mut self) {
        if let Ok(mut active) = ACTIVE.lock() {
            if active
                .as_ref()
                .and_then(Weak::upgrade)
                .is_some_and(|r| Arc::ptr_eq(&r, &self.0))
            {
                *active = None;
            }
        }
    }
}

pub(crate) fn context(cfg: &Config) -> Diagnostics {
    let mut backends: Vec<_> = cfg
        .backend_specs
        .iter()
        .map(|b| backend_name(b.kind).to_owned())
        .collect();
    backends.sort();
    backends.dedup();
    Diagnostics {
        phase: None,
        previous_run: None,
        build_commit: fingerprint(option_env!("SEINE_GIT_COMMIT").unwrap_or("unknown")),
        source_fingerprint: fingerprint(crate::runtime_identity::source_fingerprint()),
        mode: match cfg.mode {
            MiningMode::Pool => "pool",
            MiningMode::Daemon => "daemon",
        }
        .into(),
        requested_backends: backends,
        requested_cpu_threads: cfg.threads.min(65536) as u32,
        cpu_page_mode: cfg.cpu_page_mode.as_str().into(),
        cpu_affinity: match cfg.cpu_affinity {
            CpuAffinityMode::Auto => "auto",
            CpuAffinityMode::Off => "off",
            CpuAffinityMode::Os => "os",
            CpuAffinityMode::PcoreOnly => "pcore-only",
        }
        .into(),
        cpu_autotune: cfg.cpu_autotune_threads,
        uptime_secs: 0,
        reason: "periodic".into(),
        previous_run_unclean: false,
        dropped_events: 0,
        dropped_backend_samples: 0,
        events: Vec::new(),
    }
}

pub(crate) fn install(context: Diagnostics) -> Guard {
    let recorder = Arc::new(Recorder {
        started: Instant::now(),
        context,
        events: Mutex::new(BTreeMap::new()),
        dropped: AtomicU64::new(0),
        failed: AtomicBool::new(false),
        previous_unclean: AtomicBool::new(false),
        phase: Mutex::new(RunPhase::Starting),
        previous_run: Mutex::new(None),
    });
    if let Ok(mut active) = ACTIVE.lock() {
        *active = Some(Arc::downgrade(&recorder));
    }
    PANIC_HOOK.call_once(|| {
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |info| {
            // Never inspect or serialize the panic payload (it can contain secrets).
            if let Some(location) = info.location() {
                record_at(
                    DiagnosticCode::RustPanic,
                    DiagnosticKind::General,
                    None,
                    location,
                );
            }
            previous(info);
        }));
    });
    Guard(recorder)
}

fn fingerprint(value: &str) -> String {
    if !value.is_empty() && value.len() <= 64 && value.bytes().all(|b| b.is_ascii_hexdigit()) {
        value.into()
    } else {
        "unknown".into()
    }
}

pub(crate) fn backend_name(kind: BackendKind) -> &'static str {
    match kind {
        BackendKind::Cpu => "cpu",
        BackendKind::Nvidia => "nvidia",
        BackendKind::Amd => "amd",
        BackendKind::Metal => "metal",
    }
}

/// A hint only: source location + build identify the exact path for investigation.
/// The input is inspected locally; no message, substring or message hash is retained.
pub(crate) fn classify(message: &str) -> DiagnosticKind {
    let text = message
        .chars()
        .take(2048)
        .collect::<String>()
        .to_ascii_lowercase();
    if text.contains("out of memory")
        || text.contains("allocation failed")
        || text.contains("insufficient memory")
    {
        DiagnosticKind::Memory
    } else if text.contains("timed out") || text.contains("timeout") {
        DiagnosticKind::Timeout
    } else if text.contains("unauthorized") || text.contains("authentication") {
        DiagnosticKind::Authentication
    } else if text.contains("driver") {
        DiagnosticKind::Driver
    } else if text.contains("compilation")
        || text.contains("compile failed")
        || text.contains("nvrtc")
        || text.contains("hiprtc")
    {
        DiagnosticKind::Compilation
    } else if text.contains("unsupported") || text.contains("not supported") {
        DiagnosticKind::UnsupportedHardware
    } else if text.contains("share") && text.contains("reject") {
        DiagnosticKind::RejectedShare
    } else if text.contains("connect") || text.contains("socket") || text.contains("broken pipe") {
        DiagnosticKind::Connection
    } else if text.contains("tuning") || text.contains("autotune") {
        DiagnosticKind::Tuning
    } else {
        DiagnosticKind::General
    }
}

#[track_caller]
pub(crate) fn record(code: DiagnosticCode, kind: DiagnosticKind, backend: Option<&str>) {
    record_at(code, kind, backend, Location::caller());
}

fn record_at(
    code: DiagnosticCode,
    kind: DiagnosticKind,
    backend: Option<&str>,
    location: &Location<'_>,
) {
    let Ok(active) = ACTIVE.try_lock() else {
        return;
    };
    let Some(recorder) = active.as_ref().and_then(Weak::upgrade) else {
        return;
    };
    drop(active);
    recorder.record_detail(code, kind, backend, location.file(), location.line(), None);
}

/// Exact, typed context captured before errors are converted to display strings.
#[track_caller]
pub(crate) fn record_failure(
    code: DiagnosticCode,
    kind: DiagnosticKind,
    backend: Option<&str>,
    detail: FailureDetail,
) {
    let Ok(active) = ACTIVE.try_lock() else {
        return;
    };
    let Some(recorder) = active.as_ref().and_then(Weak::upgrade) else {
        return;
    };
    drop(active);
    let location = Location::caller();
    recorder.record_detail(
        code,
        kind,
        backend,
        location.file(),
        location.line(),
        Some(detail),
    );
}

pub(crate) fn set_phase(phase: RunPhase) {
    let Ok(active) = ACTIVE.try_lock() else {
        return;
    };
    if let Some(recorder) = active.as_ref().and_then(Weak::upgrade) {
        *recorder.phase.lock().unwrap_or_else(|e| e.into_inner()) = phase;
    }
}

#[track_caller]
pub(crate) fn allocation_failure(large: bool, bytes: usize, os_error: Option<i64>) {
    record_failure(
        DiagnosticCode::Warning,
        DiagnosticKind::Memory,
        Some("cpu"),
        FailureDetail {
            reason: if large {
                FailureReason::HugePagesUnavailable
            } else {
                FailureReason::AllocationFailed
            },
            operation: DiagnosticOperation::CpuAllocation,
            os_error,
            requested_bytes: Some(bytes as u64),
        },
    );
}

pub(crate) fn io_detail(operation: DiagnosticOperation, error: &std::io::Error) -> FailureDetail {
    use std::io::ErrorKind;
    let reason = if operation == DiagnosticOperation::PoolResolve {
        FailureReason::DnsFailed
    } else {
        match error.kind() {
            ErrorKind::ConnectionRefused => FailureReason::ConnectionRefused,
            ErrorKind::TimedOut => FailureReason::ConnectionTimedOut,
            ErrorKind::ConnectionReset | ErrorKind::ConnectionAborted | ErrorKind::BrokenPipe => {
                FailureReason::ConnectionReset
            }
            _ => FailureReason::IoFailed,
        }
    };
    FailureDetail {
        reason,
        operation,
        os_error: error.raw_os_error().map(i64::from),
        requested_bytes: None,
    }
}

#[track_caller]
pub(crate) fn record_io(operation: DiagnosticOperation, error: &std::io::Error) {
    record_failure(
        DiagnosticCode::Warning,
        DiagnosticKind::Connection,
        None,
        io_detail(operation, error),
    );
}

impl Recorder {
    #[cfg(test)]
    fn record(
        &self,
        code: DiagnosticCode,
        kind: DiagnosticKind,
        backend: Option<&str>,
        source: &str,
        line: u32,
    ) {
        self.record_detail(code, kind, backend, source, line, None);
    }

    fn record_detail(
        &self,
        code: DiagnosticCode,
        kind: DiagnosticKind,
        backend: Option<&str>,
        source: &str,
        line: u32,
        detail: Option<FailureDetail>,
    ) {
        if matches!(code, DiagnosticCode::RunFailed | DiagnosticCode::RustPanic) {
            self.failed.store(true, Ordering::Relaxed);
        }
        let Ok(mut events) = self.events.try_lock() else {
            self.dropped.fetch_add(1, Ordering::Relaxed);
            return;
        };
        // Rust locations on Windows use backslashes. Only normalize relative paths;
        // never strip an absolute prefix (which could reveal private filenames).
        let normalized = source.replace('\\', "/");
        let source = if seine_telemetry::valid_source(&normalized) {
            normalized.as_str()
        } else {
            "unknown"
        };
        let phase = *self.phase.lock().unwrap_or_else(|e| e.into_inner());
        let backend = backend
            .filter(|b| matches!(*b, "cpu" | "nvidia" | "amd" | "metal"))
            .map(str::to_owned);
        let key = (
            code,
            kind,
            source.to_owned(),
            line.min(1_000_000),
            backend.clone(),
            detail.clone(),
            phase,
        );
        if events.len() >= 32 && !events.contains_key(&key) {
            let is_error = !matches!(
                code,
                DiagnosticCode::Warning | DiagnosticCode::BackendWarning
            );
            if is_error || detail.is_some() {
                // Keep specific causes when generic startup warnings fill the window.
                let is_warning = |k: &&Key| {
                    matches!(
                        k.0,
                        DiagnosticCode::Warning | DiagnosticCode::BackendWarning
                    )
                };
                let victim = events
                    .keys()
                    .filter(is_warning)
                    .find(|k| k.5.is_none())
                    .or_else(|| {
                        if is_error {
                            events.keys().find(is_warning)
                        } else {
                            None
                        }
                    })
                    .cloned();
                if let Some(victim) = victim {
                    if let Some(evicted) = events.remove(&victim) {
                        self.dropped.fetch_add(evicted.count, Ordering::Relaxed);
                    }
                }
            }
            if events.len() >= 32 {
                self.dropped.fetch_add(1, Ordering::Relaxed);
                return;
            }
        }
        let now = self.started.elapsed().as_secs();
        let event = events.entry(key).or_insert_with(|| DiagnosticEvent {
            code,
            kind,
            detail,
            phase: Some(phase),
            source: source.into(),
            line: line.min(1_000_000),
            backend,
            count: 0,
            first_seen_secs: now,
            last_seen_secs: now,
        });
        event.count = event.count.saturating_add(1);
        event.last_seen_secs = now;
    }

    pub(crate) fn checkpoint(&self) -> PreviousRun {
        PreviousRun {
            phase: *self.phase.lock().unwrap_or_else(|e| e.into_inner()),
            uptime_secs: self.started.elapsed().as_secs(),
            build_commit: self.context.build_commit.clone(),
        }
    }

    pub(crate) fn set_previous_run(&self, previous: Option<PreviousRun>) {
        *self.previous_run.lock().unwrap_or_else(|e| e.into_inner()) = previous;
    }

    pub(crate) fn set_previous_unclean(&self, value: bool) {
        self.previous_unclean.store(value, Ordering::Relaxed);
    }

    pub(crate) fn snapshot(&self, final_report: bool) -> Diagnostics {
        let mut result = self.context.clone();
        result.reason = if !final_report {
            "periodic"
        } else if self.failed.load(Ordering::Relaxed) {
            "failure"
        } else {
            "shutdown"
        }
        .into();
        result.phase = Some(self.checkpoint().phase);
        result.previous_run_unclean = self.previous_unclean.swap(false, Ordering::Relaxed);
        result.previous_run = self
            .previous_run
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .take();
        result.dropped_events = self.dropped.swap(0, Ordering::Relaxed);
        if let Ok(mut events) = self.events.lock() {
            result.events = std::mem::take(&mut *events).into_values().collect();
        }
        result.uptime_secs = self.started.elapsed().as_secs();
        result
    }
}

/// Only the holder of an OS file lock owns the marker/spool. Concurrent processes
/// sharing a data directory must not label each other as crashed or delete state.
pub(crate) struct Store {
    _lock: File,
    marker: PathBuf,
    pending: PathBuf,
    attempt: PathBuf,
    checkpoint_path: PathBuf,
    pub(crate) previous_run: Option<PreviousRun>,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct Checkpoint {
    installation_id: String,
    marker_modified_ns: u64,
    run: PreviousRun,
}

fn marker_stamp(path: &Path) -> Option<u64> {
    fs::metadata(path)
        .ok()?
        .modified()
        .ok()?
        .duration_since(SystemTime::UNIX_EPOCH)
        .ok()?
        .as_nanos()
        .try_into()
        .ok()
}

impl Store {
    pub(crate) fn open(settings: &Path, installation_id: &str) -> Option<(Self, bool)> {
        let dir = settings.parent()?;
        let lock = OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(dir.join("seine.diagnostics.lock"))
            .ok()?;
        lock.try_lock().ok()?;
        let marker = dir.join("seine.diagnostics.running");
        let previous_unclean =
            fresh(&marker) && fs::read_to_string(&marker).ok().as_deref() == Some(installation_id);
        let checkpoint_path = dir.join("seine.diagnostics.phase.json");
        let previous_run = if previous_unclean && fresh(&checkpoint_path) {
            fs::metadata(&checkpoint_path)
                .ok()
                .filter(|m| m.len() <= 1024)
                .and_then(|_| fs::read(&checkpoint_path).ok())
                .and_then(|bytes| serde_json::from_slice::<Checkpoint>(&bytes).ok())
                .filter(|c| {
                    c.installation_id == installation_id
                        && Some(c.marker_modified_ns) == marker_stamp(&marker)
                        && c.run.uptime_secs <= 315_360_000
                        && fingerprint(&c.run.build_commit) == c.run.build_commit
                })
                .map(|c| c.run)
        } else {
            None
        };
        let _ = fs::remove_file(&checkpoint_path);
        fs::write(&marker, installation_id).ok()?;
        let _ = fs::remove_file(dir.join("seine.diagnostics.pending.tmp"));
        Some((
            Self {
                _lock: lock,
                marker,
                checkpoint_path,
                previous_run,
                pending: dir.join("seine.diagnostics.pending.json"),
                attempt: dir.join("seine.diagnostics.attempt"),
            },
            previous_unclean,
        ))
    }

    pub(crate) fn pending(&self, installation_id: &str) -> Option<Report> {
        let report = if fresh(&self.pending) {
            fs::metadata(&self.pending)
                .ok()
                .filter(|m| m.len() <= MAX_BODY_BYTES as u64)
                .and_then(|_| fs::read(&self.pending).ok())
                .and_then(|bytes| serde_json::from_slice::<Report>(&bytes).ok())
                .filter(|r| r.installation_id == installation_id && r.validate())
        } else {
            None
        };
        if report.is_none() {
            self.clear_pending();
        }
        report
    }

    pub(crate) fn save(&self, report: &Report) {
        if !report.validate() {
            return;
        }
        if let Ok(bytes) = serde_json::to_vec(report) {
            if bytes.len() <= MAX_BODY_BYTES {
                let temporary = self.pending.with_extension("tmp");
                if fs::write(&temporary, bytes).is_ok() {
                    let _ = fs::rename(temporary, &self.pending);
                }
            }
        }
    }
    pub(crate) fn clear_pending(&self) {
        let _ = fs::remove_file(&self.pending);
    }
    pub(crate) fn admit_upload(&self, installation_id: &str) -> bool {
        let age = fs::metadata(&self.attempt)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|time| SystemTime::now().duration_since(time).ok());
        if age.is_some_and(|age| age < Duration::from_secs(300))
            && fs::read_to_string(&self.attempt).ok().as_deref() == Some(installation_id)
        {
            return false;
        }
        fs::write(&self.attempt, installation_id).is_ok()
    }
    pub(crate) fn heartbeat(&self, installation_id: &str) {
        let _ = fs::write(&self.marker, installation_id);
    }
    pub(crate) fn checkpoint(&self, installation_id: &str, run: PreviousRun) {
        // Tie the sidecar to this exact marker write. A legacy miner can update
        // the plain marker without updating the sidecar; never attribute that
        // older checkpoint to its later run.
        self.heartbeat(installation_id);
        let Some(marker_modified_ns) = marker_stamp(&self.marker) else {
            return;
        };
        let checkpoint = Checkpoint {
            installation_id: installation_id.into(),
            marker_modified_ns,
            run,
        };
        let temp = self.checkpoint_path.with_extension("tmp");
        if let Ok(bytes) = serde_json::to_vec(&checkpoint) {
            if fs::write(&temp, bytes).is_ok() {
                let _ = fs::rename(&temp, &self.checkpoint_path);
            }
        }
    }
    pub(crate) fn finish(&self) {
        let _ = fs::remove_file(&self.checkpoint_path);
        let _ = fs::remove_file(self.checkpoint_path.with_extension("tmp"));
        let _ = fs::remove_file(&self.marker);
    }
}

fn fresh(path: &Path) -> bool {
    fs::metadata(path)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|modified| SystemTime::now().duration_since(modified).ok())
        .is_some_and(|age| age <= Duration::from_secs(86400))
}

pub(crate) fn clear_disabled(settings: &Path) {
    let Some(dir) = settings.parent() else {
        return;
    };
    // Do not interfere with another live writer; it rechecks opt-out before upload.
    let Ok(lock) = OpenOptions::new()
        .read(true)
        .write(true)
        .open(dir.join("seine.diagnostics.lock"))
    else {
        return;
    };
    if lock.try_lock().is_ok() {
        let _ = fs::remove_file(dir.join("seine.diagnostics.running"));
        let _ = fs::remove_file(dir.join("seine.diagnostics.phase.json"));
        let _ = fs::remove_file(dir.join("seine.diagnostics.phase.tmp"));
        let _ = fs::remove_file(dir.join("seine.diagnostics.pending.json"));
        let _ = fs::remove_file(dir.join("seine.diagnostics.pending.tmp"));
        let _ = fs::remove_file(dir.join("seine.diagnostics.attempt"));
    }
}

#[cfg(test)]
pub(crate) fn test_context() -> Diagnostics {
    Diagnostics {
        phase: None,
        previous_run: None,
        build_commit: "abcdef123456".into(),
        source_fingerprint: "1234abcd".into(),
        mode: "pool".into(),
        requested_backends: vec!["cpu".into()],
        requested_cpu_threads: 2,
        cpu_page_mode: "auto".into(),
        cpu_affinity: "auto".into(),
        cpu_autotune: true,
        uptime_secs: 0,
        reason: "periodic".into(),
        previous_run_unclean: false,
        dropped_events: 0,
        dropped_backend_samples: 0,
        events: vec![],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn recorder() -> Recorder {
        Recorder {
            started: Instant::now(),
            context: test_context(),
            events: Mutex::new(BTreeMap::new()),
            dropped: AtomicU64::new(0),
            failed: AtomicBool::new(false),
            previous_unclean: AtomicBool::new(false),
            phase: Mutex::new(RunPhase::Starting),
            previous_run: Mutex::new(None),
        }
    }

    #[test]
    fn structured_causes_separate_errors_at_one_site_and_normalize_windows_sources() {
        let recorder = recorder();
        *recorder.phase.lock().unwrap() = RunPhase::InitializingBackends;
        for errno in [12, 13, 12] {
            recorder.record_detail(
                DiagnosticCode::Warning,
                DiagnosticKind::Memory,
                Some("cpu"),
                r"src\backend\cpu\kernel.rs",
                10,
                Some(FailureDetail {
                    reason: FailureReason::HugePagesUnavailable,
                    operation: DiagnosticOperation::CpuAllocation,
                    requested_bytes: Some(2147483648),
                    os_error: Some(errno),
                }),
            );
        }
        let snapshot = recorder.snapshot(false);
        assert_eq!(snapshot.events.len(), 2);
        assert_eq!(snapshot.events.iter().map(|e| e.count).sum::<u64>(), 3);
        assert!(snapshot
            .events
            .iter()
            .all(|e| e.source == "src/backend/cpu/kernel.rs"
                && e.phase == Some(RunPhase::InitializingBackends)));
        let mut report: Report =
            serde_json::from_str(include_str!("../telemetry/fixture.json")).unwrap();
        report.schema_version = seine_telemetry::SCHEMA_VERSION;
        report.diagnostics = Some(snapshot);
        assert!(report.validate());
        let json = serde_json::to_vec(&report).unwrap();
        assert!(serde_json::from_slice::<Report>(&json).unwrap().validate());
        recorder.record(
            DiagnosticCode::Warning,
            DiagnosticKind::General,
            None,
            r"C:\Users\alice\src\private.rs",
            1,
        );
        assert_eq!(recorder.snapshot(false).events[0].source, "unknown");
    }

    #[test]
    fn specific_cause_displaces_generic_warning_at_capacity() {
        let recorder = recorder();
        for line in 0..32 {
            recorder.record(
                DiagnosticCode::Warning,
                DiagnosticKind::General,
                None,
                "src/miner/mod.rs",
                line,
            );
        }
        recorder.record_detail(
            DiagnosticCode::Warning,
            DiagnosticKind::Memory,
            Some("cpu"),
            "src/backend/cpu/kernel.rs",
            100,
            Some(FailureDetail::new(
                FailureReason::HugePagesUnavailable,
                DiagnosticOperation::CpuAllocation,
            )),
        );
        let snapshot = recorder.snapshot(false);
        assert_eq!(snapshot.events.len(), 32);
        assert_eq!(snapshot.dropped_events, 1);
        assert!(snapshot.events.iter().any(|e| e.detail.is_some()));
    }

    #[test]
    fn io_details_preserve_codes_without_error_text() {
        for (kind, reason) in [
            (
                std::io::ErrorKind::ConnectionRefused,
                FailureReason::ConnectionRefused,
            ),
            (
                std::io::ErrorKind::TimedOut,
                FailureReason::ConnectionTimedOut,
            ),
            (
                std::io::ErrorKind::BrokenPipe,
                FailureReason::ConnectionReset,
            ),
        ] {
            let error = std::io::Error::new(kind, "PRIVATE https://user:password@host/wallet");
            let detail = io_detail(DiagnosticOperation::PoolConnect, &error);
            assert_eq!(detail.reason, reason);
            assert!(!serde_json::to_string(&detail).unwrap().contains("PRIVATE"));
        }
        let detail = io_detail(
            DiagnosticOperation::PoolResolve,
            &std::io::Error::from_raw_os_error(13),
        );
        assert_eq!(detail.reason, FailureReason::DnsFailed);
        assert_eq!(detail.os_error, Some(13));
    }

    #[test]
    fn bounded_counters_deduplicate_and_never_retain_messages_or_local_paths() {
        let recorder = recorder();
        let secret = "driver failure for wallet SECRET at /home/alice/private/config";
        for _ in 0..100 {
            recorder.record(
                DiagnosticCode::Warning,
                classify(secret),
                Some("nvidia"),
                "src/miner/mod.rs",
                10,
            );
        }
        recorder.record(
            DiagnosticCode::Error,
            classify(secret),
            Some(secret),
            "/home/alice/private.rs",
            20,
        );
        let result = recorder.snapshot(false);
        assert_eq!(result.events.len(), 2);
        assert_eq!(result.events[0].count, 100);
        let json = serde_json::to_string(&result).unwrap();
        assert!(!json.contains("SECRET") && !json.contains("alice") && !json.contains("private"));
        assert!(result
            .events
            .iter()
            .all(|e| e.kind == DiagnosticKind::Driver));
        assert!(recorder.snapshot(false).events.is_empty());
        for line in 1..=40 {
            recorder.record(
                DiagnosticCode::Warning,
                DiagnosticKind::General,
                None,
                "src/miner/mod.rs",
                line,
            );
        }
        let result = recorder.snapshot(false);
        assert_eq!(result.events.len(), 32);
        assert_eq!(result.dropped_events, 8);
        for line in 1..=32 {
            recorder.record(
                DiagnosticCode::Warning,
                DiagnosticKind::General,
                None,
                "src/miner/mod.rs",
                line,
            );
        }
        recorder.record(
            DiagnosticCode::RunFailed,
            DiagnosticKind::General,
            None,
            "src/miner/mod.rs",
            99,
        );
        let result = recorder.snapshot(true);
        assert_eq!(result.events.len(), 32);
        assert!(result
            .events
            .iter()
            .any(|e| e.code == DiagnosticCode::RunFailed));
        assert_eq!(result.dropped_events, 1);
    }

    #[test]
    fn failures_and_unclean_markers_survive_short_sessions() {
        let recorder = recorder();
        recorder.set_previous_unclean(true);
        recorder.record(
            DiagnosticCode::RunFailed,
            DiagnosticKind::Connection,
            None,
            "src/miner/mod.rs",
            1,
        );
        let snapshot = recorder.snapshot(true);
        assert_eq!(snapshot.reason, "failure");
        assert!(snapshot.previous_run_unclean);
        assert!(!recorder.snapshot(true).previous_run_unclean);
        let mut report: Report =
            serde_json::from_str(include_str!("../telemetry/fixture.json")).unwrap();
        report.schema_version = seine_telemetry::SCHEMA_VERSION;
        report.window_secs = 1;
        report.backends.clear();
        report.diagnostics = Some(snapshot);
        assert!(report.validate());
    }

    #[test]
    fn persistence_is_exclusive_identity_bound_and_replays_exact_report_id() {
        struct Temp(PathBuf);
        impl Drop for Temp {
            fn drop(&mut self) {
                let _ = fs::remove_dir_all(&self.0);
            }
        }
        let dir = Temp(std::env::temp_dir().join(format!(
                "seine-diagnostics-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            )));
        fs::create_dir(&dir.0).unwrap();
        let settings = dir.0.join("seine.telemetry.json");
        let report: Report =
            serde_json::from_str(include_str!("../telemetry/fixture.json")).unwrap();
        let (store, unclean) = Store::open(&settings, &report.installation_id).unwrap();
        assert!(!unclean);
        assert!(Store::open(&settings, &report.installation_id).is_none());
        assert!(store.admit_upload(&report.installation_id));
        assert!(!store.admit_upload(&report.installation_id));
        let marker = File::options().write(true).open(&store.marker).unwrap();
        marker
            .set_modified(SystemTime::now() - Duration::from_secs(86401))
            .unwrap();
        assert!(!fresh(&store.marker));
        store.heartbeat(&report.installation_id);
        assert!(fresh(&store.marker));
        store.save(&report);
        assert_eq!(
            store.pending(&report.installation_id).unwrap().report_id,
            report.report_id
        );
        store.checkpoint(
            &report.installation_id,
            PreviousRun {
                phase: RunPhase::Tuning,
                uptime_secs: 42,
                build_commit: "abcdef".into(),
            },
        );
        drop(store); // Simulated abnormal exit: no finish().
        let (store, unclean) = Store::open(&settings, &report.installation_id).unwrap();
        assert!(unclean);
        let previous = store.previous_run.as_ref().unwrap();
        assert_eq!(previous.phase, RunPhase::Tuning);
        assert_eq!(previous.uptime_secs, 42);
        assert_eq!(previous.build_commit, "abcdef");
        assert!(store.pending("changed-destination-id").is_none());
        assert!(!store.pending.exists());
        store.finish();
        drop(store);
        let (store, unclean) = Store::open(&settings, &report.installation_id).unwrap();
        assert!(!unclean);
        assert!(store.previous_run.is_none());
        store.save(&report);
        let file = File::options().write(true).open(&store.pending).unwrap();
        file.set_modified(SystemTime::now() - Duration::from_secs(86401))
            .unwrap();
        assert!(store.pending(&report.installation_id).is_none());
        store.finish();
    }
    #[test]
    fn checkpoint_requires_matching_fresh_marker_and_bounded_valid_context() {
        let dir = std::env::temp_dir().join(format!("seine-checkpoint-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let settings = dir.join("settings.json");
        let id = "11111111111111111111111111111111";
        for content in [
            r#"{"installation_id":"other","run":{"phase":"mining","uptime_secs":5,"build_commit":"abcdef"}}"#.to_string(),
            "PRIVATE".repeat(300),
            r#"{"installation_id":"11111111111111111111111111111111","run":{"phase":"mining","uptime_secs":5,"build_commit":"PRIVATE"}}"#.to_string(),
        ] {
            fs::write(dir.join("seine.diagnostics.running"), id).unwrap();
            fs::write(dir.join("seine.diagnostics.phase.json"), content).unwrap();
            let (store, unclean) = Store::open(&settings, id).unwrap();
            assert!(unclean);
            assert!(store.previous_run.is_none());
            store.finish();
        }
        let (store, _) = Store::open(&settings, id).unwrap();
        store.checkpoint(
            id,
            PreviousRun {
                phase: RunPhase::Mining,
                uptime_secs: 90,
                build_commit: "abcdef".into(),
            },
        );
        drop(store);
        // Simulate a legacy writer starting another run with no phase sidecar.
        let file = File::options()
            .write(true)
            .open(dir.join("seine.diagnostics.running"))
            .unwrap();
        file.set_modified(SystemTime::now() - Duration::from_secs(1))
            .unwrap();
        let (store, unclean) = Store::open(&settings, id).unwrap();
        assert!(unclean);
        assert!(store.previous_run.is_none());
        store.checkpoint(
            id,
            PreviousRun {
                phase: RunPhase::Mining,
                uptime_secs: 90,
                build_commit: "abcdef".into(),
            },
        );
        drop(store);
        let file = File::options()
            .write(true)
            .open(dir.join("seine.diagnostics.running"))
            .unwrap();
        file.set_modified(SystemTime::now() - Duration::from_secs(86401))
            .unwrap();
        let (store, unclean) = Store::open(&settings, id).unwrap();
        assert!(!unclean);
        assert!(store.previous_run.is_none());
        store.finish();
        drop(store);
        fs::remove_dir_all(dir).unwrap();
    }
}
