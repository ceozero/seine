//! Bounded kernel trials on productive work, serialized with worker-count trials.
//! Architecture eligibility permits a trial; only repeated gains select a path.
use super::*;
use crate::backend::cpu::CpuAdaptiveSnapshot;
use blocknet_pow_kernel::CpuKernel;

const RECHECK_SECS: u64 = 30 * 60;
const RETRY_SECS: u64 = 5 * 60;
const MAX_TRIAL_SECS: u64 = 10 * 60;
const MAX_DRIFT: f64 = 0.05;

const CACHE_SCHEMA: u32 = 3;

// Validated policy, restricted to the native Turin measurement identity.
// Slow samples and explicitly lengthened trials retain the existing window.
fn short_trials_for(
    identity: &crate::runtime_identity::CpuIdentity,
    candidates: &[CpuKernel],
    configured_secs: u64,
) -> bool {
    configured_secs == 6
        && identity.vendor.as_deref() == Some("AuthenticAMD")
        && identity.family == Some(0x1a)
        && identity.model == Some(0x02)
        && candidates.contains(&CpuKernel::Avx512256Stream)
}

fn sample_ready(sample: Sample, window_secs: u64, short_trials: bool) -> bool {
    (sample.secs >= window_secs && sample.hashes >= 32)
        || (short_trials && sample.secs >= 10 && sample.hashes >= 256)
}

// ARM starts on the portable NEON path; SHA3 is eligible only after runtime
// feature detection and must win two productive-work comparisons before it
// becomes the cached choice.
fn supported_kernels() -> Vec<CpuKernel> {
    CpuKernel::ALL
        .into_iter()
        .filter(|k| k.is_supported())
        .collect()
}

#[cfg(test)]
fn candidates() -> Vec<CpuKernel> {
    // Synthetic policy fixtures explicitly use the identity-neutral set.
    candidates_for(
        &crate::runtime_identity::CpuIdentity::default(),
        &supported_kernels(),
    )
}

fn candidates_for(
    identity: &crate::runtime_identity::CpuIdentity,
    supported: &[CpuKernel],
) -> Vec<CpuKernel> {
    let mut paths: Vec<_> = [
        CpuKernel::Avx512,
        CpuKernel::Avx2,
        CpuKernel::Neon,
        CpuKernel::NeonSha3,
    ]
    .into_iter()
    .filter(|k| supported.contains(k))
    .collect();
    // Genoa 9R14 VM: +2.85% cold / +7.99% cached productive mining;
    // Turin and Ryzen also have repeated wins. See genoa-streaming-20261025.
    // Identity limits automatic experiments; the independent ISA/OS support
    // check remains mandatory. Turin needs a measured win per worker
    // count/backing; validated Ryzen also starts on it (`startup_kernel_for`).
    if identity.vendor.as_deref() == Some("AuthenticAMD")
        && matches!(
            (identity.family, identity.model),
            (Some(0x19), Some(0x11)) | (Some(0x1a), Some(0x02 | 0x44))
        )
        && supported.contains(&CpuKernel::Avx512256Stream)
    {
        if identity.model == Some(0x02) {
            // Turin: test the measured high-concurrency challenger before AVX2.
            // Ordering changes discovery cost, never the repeated-win gate.
            let before_avx2 = paths
                .iter()
                .position(|k| *k == CpuKernel::Avx2)
                .unwrap_or(paths.len());
            paths.insert(before_avx2, CpuKernel::Avx512256Stream);
        } else {
            paths.push(CpuKernel::Avx512256Stream);
        }
    }
    paths
}

// Validated desktop Zen 5 (Ryzen 9950X3D, family 1Ah, model 44h): native
// fixed-kernel runs measured streaming 38-46% faster than every uniform kernel
// at 8 and 16 workers, but live A/B/A trials on a busy desktop rarely clear the
// baseline-drift gate. Start such contexts on streaming. The other candidates
// still get the usual two comparisons against it. Lower counts are unmeasured.
const STARTUP_STREAM_MIN_WORKERS: usize = 8;

fn startup_kernel_for(
    identity: &crate::runtime_identity::CpuIdentity,
    candidates: &[CpuKernel],
) -> Option<CpuKernel> {
    (identity.vendor.as_deref() == Some("AuthenticAMD")
        && identity.family == Some(0x1a)
        && identity.model == Some(0x44)
        && candidates.contains(&CpuKernel::Avx512256Stream))
    .then_some(CpuKernel::Avx512256Stream)
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
struct Context {
    // Indices in the controller's stable CPU backend list. Different survivors
    // may have different affinity even with identical worker/backing vectors.
    members: Vec<usize>,
    workers: Vec<usize>,
    backing: Vec<[u64; 5]>,
}

impl Context {
    fn same_workers(&self, other: &Self) -> bool {
        self.members == other.members && self.workers == other.workers
    }

    fn from_snapshots(snapshots: &[CpuAdaptiveSnapshot]) -> Self {
        Self {
            members: snapshots
                .iter()
                .enumerate()
                .filter_map(|(index, s)| s.running.then_some(index))
                .collect(),
            workers: snapshots
                .iter()
                .filter(|s| s.running)
                .map(|s| s.threads)
                .collect(),
            backing: snapshots
                .iter()
                .filter(|s| s.running)
                .map(|s| s.backing_bytes)
                .collect(),
        }
    }
}

#[derive(Clone, Serialize, Deserialize)]
struct Winner {
    context: Context,
    kernel: String,
    timestamp: u64,
    base: String,
    candidate: String,
    samples: Vec<Sample>,
}

#[derive(Serialize, Deserialize)]
struct Cache {
    schema: u32,
    host: CpuAutotuneHostFingerprint,
    configuration: String,
    winners: Vec<Winner>,
}

impl Cache {
    fn compatible(&self, host: &CpuAutotuneHostFingerprint, configuration: &str) -> bool {
        self.schema == CACHE_SCHEMA && self.host == *host && self.configuration == configuration
    }

    fn winner(&self, context: &Context, now: u64, paths: &[CpuKernel]) -> Option<CpuKernel> {
        self.winners.iter().rev().find_map(|winner| {
            let kernel = winner.kernel.parse::<CpuKernel>().ok()?;
            (winner.context == *context
                && winner.timestamp <= now
                && now - winner.timestamp < CPU_AUTOTUNE_RECORD_MAX_AGE_SECS
                && paths.contains(&kernel)
                && winner.samples.iter().all(|s| s.secs > 0 && s.hashes > 0)
                && if winner.kernel == winner.base {
                    match winner.samples.as_slice() {
                        [a, b, c] => comparison(*a, *b, *c) == Comparison::NoConfirmedGain,
                        [a, b, c, d, e, f] => {
                            improves(*a, *b, *c)
                                && comparison(*d, *e, *f) == Comparison::NoConfirmedGain
                        }
                        _ => false,
                    }
                } else {
                    winner.kernel == winner.candidate
                        && winner.samples.len() == 6
                        && improves(winner.samples[0], winner.samples[1], winner.samples[2])
                        && improves(winner.samples[3], winner.samples[4], winner.samples[5])
                })
            .then_some(kernel)
        })
    }
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
struct Sample {
    hashes: u64,
    secs: u64,
}

impl Sample {
    fn hps(self) -> f64 {
        self.hashes as f64 / self.secs.max(1) as f64
    }
}

// Two A/B/A comparisons are required; each has a fresh baseline. One favourable
// window cannot promote a path. Baseline drift and hash quantization are gated.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Comparison {
    Gain,
    NoConfirmedGain,
    Inconclusive,
}

// Rates behind each decision, so productive trials can be audited from logs.
fn rates(samples: &[Sample], base: CpuKernel, candidate: CpuKernel) -> String {
    samples
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let kernel = if i % 3 == 1 { candidate } else { base };
            format!("{kernel} {:.2}", s.hps())
        })
        .collect::<Vec<_>>()
        .join(" / ")
}

fn improves(before: Sample, candidate: Sample, after: Sample) -> bool {
    comparison(before, candidate, after) == Comparison::Gain
}

fn comparison(before: Sample, candidate: Sample, after: Sample) -> Comparison {
    if [before, candidate, after]
        .iter()
        .any(|s| s.secs == 0 || s.hashes == 0)
    {
        return Comparison::Inconclusive;
    }
    if (after.hps() / before.hps() - 1.0).abs() > MAX_DRIFT {
        return Comparison::Inconclusive;
    }
    let baseline =
        (before.hashes as f64 + after.hashes as f64) / (before.secs as f64 + after.secs as f64);
    let quantization =
        1.0 / before.secs as f64 + 1.0 / candidate.secs as f64 + 1.0 / after.secs as f64;
    if candidate.hps() > baseline * 1.02 + quantization {
        Comparison::Gain
    } else {
        Comparison::NoConfirmedGain
    }
}

struct Trial {
    context: Context,
    base: CpuKernel,
    candidate: CpuKernel,
    started: u64,
    samples: Vec<Sample>,
    window: Option<(u64, u64, Vec<u64>)>,
    idle_since: Option<u64>,
}

impl Trial {
    fn requested(&self) -> CpuKernel {
        if self.samples.len() % 3 == 1 {
            self.candidate
        } else {
            self.base
        }
    }
}

#[derive(Default)]
pub(super) struct Action {
    pub hold_counts: bool,
    pub kernel: Option<CpuKernel>,
    pub reset_scores: bool,
    pub interrupted: bool,
    pub message: Option<String>,
}

pub(super) struct Tuner {
    cache: Cache,
    path: std::path::PathBuf,
    trial: Option<Trial>,
    checked: Option<Context>,
    next_check: u64,
    retries: Vec<(Context, u64)>,
    window_secs: u64,
    short_trials: bool,
    candidates: Vec<CpuKernel>,
    // Remaining challengers for this count/backing. Cache only a complete sweep.
    pending: Vec<CpuKernel>,
    // Cached/final winners must finish switching before thread sampling resumes.
    settling: Option<CpuKernel>,
    settle_started: u64,
    // Identity-validated starting path for uncached contexts, if any.
    startup: Option<CpuKernel>,
}

impl Tuner {
    pub(super) fn new(cfg: &Config, host: CpuAutotuneHostFingerprint) -> Self {
        Self::for_identity(cfg, host, &crate::runtime_identity::cpu_identity())
    }

    #[cfg(test)]
    pub(super) fn identity_neutral(cfg: &Config, host: CpuAutotuneHostFingerprint) -> Self {
        Self::for_identity(cfg, host, &crate::runtime_identity::CpuIdentity::default())
    }

    fn for_identity(
        cfg: &Config,
        host: CpuAutotuneHostFingerprint,
        identity: &crate::runtime_identity::CpuIdentity,
    ) -> Self {
        // Native hardware tests must exercise the shipping identity and ISA
        // gates. Only synthetic fixtures opt into an identity-neutral tuner.
        let candidates = candidates_for(identity, &supported_kernels());
        let startup = startup_kernel_for(identity, &candidates);
        let short_trials = short_trials_for(identity, &candidates, cfg.cpu_autotune_secs);
        let mut configuration = format!(
            "profile={:?};pages={:?};affinity={:?};cpu={:?};batch={};control={};flush={:?};kernels={:?}",
            cfg.cpu_profile,
            cfg.cpu_page_mode,
            cfg.cpu_affinity,
            cfg.backend_specs
                .iter()
                .filter(|s| s.kind == BackendKind::Cpu)
                .map(|s| s.cpu_affinity.unwrap_or(cfg.cpu_affinity))
                .collect::<Vec<_>>(),
            cfg.cpu_hash_batch_size,
            cfg.cpu_control_check_interval_hashes,
            cfg.cpu_hash_flush_interval,
            candidates,
        );
        if short_trials {
            configuration.push_str(";sample_policy=turin-10s-256-v1");
        }
        let mut name = cfg.cpu_autotune_config_path.as_os_str().to_owned();
        name.push(".kernels.json");
        let path = std::path::PathBuf::from(name);
        let cache = fs::read(&path)
            .ok()
            .and_then(|raw| serde_json::from_slice::<Cache>(&raw).ok())
            .filter(|record| record.compatible(&host, &configuration))
            .unwrap_or(Cache {
                schema: CACHE_SCHEMA,
                host,
                configuration,
                winners: Vec::new(),
            });
        Self {
            cache,
            path,
            trial: None,
            checked: None,
            next_check: 0,
            retries: Vec::new(),
            window_secs: cfg.cpu_autotune_secs.saturating_mul(5).clamp(30, 60),
            short_trials,
            candidates,
            pending: Vec::new(),
            settling: None,
            settle_started: 0,
            startup,
        }
    }

    fn save(&mut self, trial: Trial, kernel: CpuKernel) {
        let context = trial.context;
        self.cache
            .winners
            .retain(|winner| winner.context != context);
        self.cache.winners.push(Winner {
            context,
            kernel: kernel.to_string(),
            timestamp: unix_secs(),
            base: trial.base.to_string(),
            candidate: trial.candidate.to_string(),
            samples: trial.samples,
        });
        // Bound disk use even if memory backing varies continually.
        if self.cache.winners.len() > 64 {
            self.cache.winners.remove(0);
        }
        let result = (|| -> Result<()> {
            if let Some(parent) = self.path.parent().filter(|p| !p.as_os_str().is_empty()) {
                fs::create_dir_all(parent)?;
            }
            let temp = self
                .path
                .with_extension(format!("{}.tmp", std::process::id()));
            fs::write(&temp, serde_json::to_vec_pretty(&self.cache)?)?;
            if let Err(err) = fs::rename(&temp, &self.path) {
                let _ = fs::remove_file(&temp);
                return Err(err.into());
            }
            Ok(())
        })();
        if let Err(err) = result {
            warn(
                "MINER",
                format!("cpu-autotune | could not save kernel selection: {err:#}"),
            );
        }
    }

    fn finish_comparison(&mut self, trial: Trial, kernel: CpuKernel, now: u64) {
        if self.pending.is_empty() {
            self.save(trial, kernel);
            self.next_check = now + RECHECK_SECS;
        } else {
            // Keep count trials paused until every eligible challenger has had
            // its own A/B/A comparison. A partial sweep must not hide the third
            // path behind a cached winner or a thirty-minute recheck delay.
            self.next_check = now;
        }
    }

    pub(super) fn joint_budget_secs(&self) -> u64 {
        // Two A/B/A cycles per challenger, one retry cooldown and switch slack.
        // Outer count windows are budgeted separately by the count policy.
        self.window_secs
            .saturating_mul(6)
            .saturating_mul(self.candidates.len().saturating_sub(1) as u64)
            .saturating_add(RETRY_SECS)
            .saturating_add(120)
    }

    #[cfg(test)]
    pub(super) fn test_candidates(&mut self, paths: Vec<CpuKernel>) {
        self.candidates = paths;
    }

    pub(super) fn is_comparing(&self) -> bool {
        self.trial.is_some() || self.settling.is_some() || !self.pending.is_empty()
    }

    pub(super) fn forget_previous_members(&mut self, now: u64) {
        // The caller already aborted/restored the old comparison. Its retry
        // delay must not let a new membership's count probes bypass kernel
        // selection and incorrectly reject a count on its incumbent path.
        debug_assert!(!self.is_comparing());
        self.pending.clear();
        self.checked = None;
        self.retries.clear();
        self.next_check = now;
    }

    fn defer_retry(&mut self, now: u64, context: Context) {
        self.retries
            .retain(|(old, until)| *until > now && !old.same_workers(&context));
        self.retries.push((context, now.saturating_add(RETRY_SECS)));
        if self.retries.len() > 64 {
            self.retries.remove(0);
        }
    }

    pub(super) fn retry_pending(&self, now: u64, snapshots: &[CpuAdaptiveSnapshot]) -> bool {
        !self.retries.is_empty()
            && self.context_retry_pending(now, &Context::from_snapshots(snapshots))
    }

    fn context_retry_pending(&self, now: u64, context: &Context) -> bool {
        self.retries
            .iter()
            .any(|(old, until)| now < *until && old.same_workers(context))
    }

    pub(super) fn abort(&mut self, now: u64) -> Action {
        let trial = self.trial.take();
        let context = trial
            .as_ref()
            .map(|trial| trial.context.clone())
            .or_else(|| {
                (self.settling.is_some() || !self.pending.is_empty())
                    .then(|| self.checked.clone())
                    .flatten()
            });
        let base = trial.map(|trial| trial.base);
        if let Some(context) = context {
            self.defer_retry(now, context);
            // Do not let an interrupted new context inherit an older, longer
            // recheck. An idle cancellation has no comparison to reschedule.
            self.next_check = now.saturating_add(RETRY_SECS);
        }
        self.settling = None;
        self.pending.clear();
        Action {
            kernel: base,
            reset_scores: false,
            interrupted: true,
            message: base.map(|_| "kernel comparison interrupted; keeping previous path".into()),
            ..Action::default()
        }
    }

    pub(super) fn tick(
        &mut self,
        now: u64,
        snapshots: &[CpuAdaptiveSnapshot],
        ready: bool,
        allow_start: bool,
    ) -> Action {
        let context = Context::from_snapshots(snapshots);
        let retry_pending = self.context_retry_pending(now, &context);
        let active: Vec<_> = snapshots.iter().filter(|s| s.running).copied().collect();
        let snapshots = active.as_slice();
        if snapshots.is_empty() || self.candidates.len() < 2 {
            return Action::default();
        }
        let hashes: u64 = snapshots.iter().map(|s| s.hashes).sum();
        if let Some(kernel) = self.settling {
            if ready
                && snapshots
                    .iter()
                    .all(|s| s.kernel == kernel && s.kernel_ready)
            {
                self.settling = None;
                return Action {
                    hold_counts: !self.pending.is_empty(),
                    ..Action::default()
                };
            }
            if now.saturating_sub(self.settle_started) >= MAX_TRIAL_SECS {
                return self.abort(now);
            }
            return Action {
                hold_counts: true,
                ..Action::default()
            };
        }
        if let Some(trial) = &self.trial {
            if context != trial.context || now.saturating_sub(trial.started) >= MAX_TRIAL_SECS {
                return self.abort(now);
            }
        }
        if self.trial.is_none() {
            if retry_pending || !allow_start || !ready || !snapshots.iter().all(|s| s.kernel_ready)
            {
                return Action::default();
            }
            let changed = self.checked.as_ref() != Some(&context);
            if now < self.next_check && !changed {
                return Action::default();
            }
            // When a worker count/backing changes, reuse only that exact context.
            if changed {
                self.pending.clear();
                if let Some(kernel) = self.cache.winner(&context, unix_secs(), &self.candidates) {
                    self.checked = Some(context);
                    self.next_check = now + RECHECK_SECS;
                    if snapshots.iter().all(|s| s.kernel == kernel) {
                        return Action::default();
                    }
                    self.settling = Some(kernel);
                    self.settle_started = now;
                    return Action {
                        hold_counts: true, kernel: Some(kernel), reset_scores: true, interrupted: false,
                        message: Some(format!("restoring confirmed {kernel} path for this worker count and memory backing")),
                    };
                }
                if let Some(kernel) = self.startup.filter(|k| {
                    self.candidates.contains(k)
                        && context
                            .workers
                            .iter()
                            .all(|&w| w >= STARTUP_STREAM_MIN_WORKERS)
                        && !snapshots.iter().all(|s| s.kernel == *k)
                }) {
                    // Compare the remaining paths against it promptly; only a
                    // completed sweep is cached.
                    self.checked = Some(context);
                    self.next_check = now;
                    self.settling = Some(kernel);
                    self.settle_started = now;
                    return Action {
                        hold_counts: true, kernel: Some(kernel), reset_scores: true, interrupted: false,
                        message: Some(format!("starting {kernel} path validated for this CPU; comparing other paths against it")),
                    };
                }
            }
            let base = snapshots[0].kernel;
            if !snapshots.iter().all(|s| s.kernel == base) {
                return Action::default();
            }
            if self.pending.is_empty() {
                self.pending = self
                    .candidates
                    .iter()
                    .copied()
                    .filter(|&k| k != base)
                    .collect();
            }
            if self.pending.is_empty() {
                return Action::default();
            }
            let candidate = self.pending.remove(0);
            self.checked = Some(context.clone());
            self.trial = Some(Trial {
                context,
                base,
                candidate,
                started: now,
                samples: Vec::new(),
                window: None,
                idle_since: None,
            });
            return Action {
                hold_counts: true,
                message: Some(format!("comparing {base} and {candidate} while mining")),
                ..Action::default()
            };
        }
        let trial = self.trial.as_mut().unwrap();
        let requested = trial.requested();
        if !ready {
            let idle = trial.idle_since.get_or_insert(now);
            if now.saturating_sub(*idle) >= 3 {
                return self.abort(now);
            }
            return Action {
                hold_counts: true,
                ..Action::default()
            };
        }
        trial.idle_since = None;
        if !snapshots
            .iter()
            .all(|s| s.kernel == requested && s.kernel_ready)
        {
            trial.window = None;
            return Action {
                hold_counts: true,
                ..Action::default()
            };
        }
        let generations: Vec<_> = snapshots.iter().map(|s| s.kernel_generation).collect();
        let Some((start, first, observed_generations)) = &trial.window else {
            trial.window = Some((now, hashes, generations));
            return Action {
                hold_counts: true,
                ..Action::default()
            };
        };
        if observed_generations != &generations || hashes < *first {
            return self.abort(now);
        }
        let sample = Sample {
            hashes: hashes - *first,
            secs: now.saturating_sub(*start),
        };
        if !sample_ready(sample, self.window_secs, self.short_trials) {
            return Action {
                hold_counts: true,
                ..Action::default()
            };
        }
        trial.window = None;
        trial.samples.push(sample);
        if trial.samples.len() == 3
            && !improves(trial.samples[0], trial.samples[1], trial.samples[2])
        {
            // Reject an inconclusive/noisy candidate without spending a second cycle.
            let trial = self.trial.take().unwrap();
            let stable = comparison(trial.samples[0], trial.samples[1], trial.samples[2])
                == Comparison::NoConfirmedGain;
            let measured = rates(&trial.samples, trial.base, trial.candidate);
            if stable {
                let base = trial.base;
                self.finish_comparison(trial, base, now);
            } else {
                self.pending.clear();
                self.next_check = now + RETRY_SECS;
                self.defer_retry(now, trial.context);
            }
            return Action {
                hold_counts: !self.pending.is_empty(),
                interrupted: !stable,
                message: Some(if stable {
                    format!("keeping current kernel; no confirmed gain ({measured} H/s)")
                } else {
                    format!("keeping current kernel; baseline drifted, retrying sooner ({measured} H/s)")
                }),
                ..Action::default()
            };
        }
        if trial.samples.len() == 6 {
            let trial = self.trial.take().unwrap();
            let outcome = comparison(trial.samples[3], trial.samples[4], trial.samples[5]);
            let measured = rates(&trial.samples, trial.base, trial.candidate);
            let promoted = outcome == Comparison::Gain;
            let conclusive = outcome != Comparison::Inconclusive;
            let kernel = if promoted {
                trial.candidate
            } else {
                trial.base
            };
            if conclusive {
                self.finish_comparison(trial, kernel, now);
            } else {
                self.pending.clear();
                self.next_check = now + RETRY_SECS;
                self.defer_retry(now, trial.context);
            }
            self.settling = Some(kernel);
            self.settle_started = now;
            return Action {
                hold_counts: true,
                kernel: Some(kernel),
                reset_scores: promoted,
                interrupted: !conclusive,
                message: Some(if promoted {
                    format!("confirmed faster {kernel} path in two comparisons ({measured} H/s)")
                } else if conclusive {
                    format!("keeping {kernel}; gain did not repeat ({measured} H/s)")
                } else {
                    format!("keeping {kernel}; confirmation was noisy, retrying sooner ({measured} H/s)")
                }),
            };
        }
        Action {
            hold_counts: true,
            kernel: Some(trial.requested()),
            ..Action::default()
        }
    }
}

fn unix_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn short_trial_policy_is_limited_to_turin_default_timing_and_supported_path() {
        use crate::runtime_identity::CpuIdentity;
        let turin = CpuIdentity {
            vendor: Some("AuthenticAMD".into()),
            family: Some(0x1a),
            model: Some(0x02),
            ..CpuIdentity::default()
        };
        let paths = [CpuKernel::Avx512, CpuKernel::Avx512256Stream];
        assert!(short_trials_for(&turin, &paths, 6));
        assert!(!short_trials_for(&turin, &paths, 12));
        assert!(!short_trials_for(&turin, &[CpuKernel::Avx2], 6));
        for other in [
            CpuIdentity {
                model: Some(0x44),
                ..turin.clone()
            },
            CpuIdentity {
                family: Some(0x19),
                model: Some(0x11),
                ..turin.clone()
            },
            CpuIdentity {
                vendor: Some("GenuineIntel".into()),
                ..turin.clone()
            },
            CpuIdentity::default(),
        ] {
            assert!(!short_trials_for(&other, &paths, 6));
        }
    }

    #[test]
    fn fast_samples_need_time_and_count_while_slow_samples_keep_original_rule() {
        for (secs, hashes, short, expected) in [
            (9, 500, true, false),
            (10, 255, true, false),
            (10, 256, true, true),
            (10, 500, false, false),
            (29, 255, true, false),
            (30, 31, true, false),
            (30, 32, true, true),
            (30, 32, false, true),
        ] {
            assert_eq!(sample_ready(Sample { secs, hashes }, 30, short), expected);
        }
    }

    #[test]
    fn short_samples_still_need_two_promotions_and_kernel_acknowledgements() {
        let mut t = tuner();
        t.short_trials = true;
        t.candidates = vec![CpuKernel::Avx512, CpuKernel::Avx2];
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        assert!(t.tick(now, &[s], true, true).hold_counts);
        for (index, rate) in [100, 120, 100, 100, 120, 100].into_iter().enumerate() {
            now += 1;
            s.kernel_ready = false;
            assert!(t.tick(now, &[s], true, true).hold_counts);
            assert!(t.trial.as_ref().unwrap().window.is_none());
            s.kernel_ready = true;
            t.tick(now, &[s], true, true);
            now += 10;
            s.hashes += rate * 10;
            let action = t.tick(now, &[s], true, true);
            if let Some(kernel) = action.kernel {
                s.kernel = kernel;
                s.kernel_generation += 1;
            }
            if index < 5 {
                assert!(t.cache.winners.is_empty());
            }
        }
        assert_eq!(s.kernel, CpuKernel::Avx2);
        assert_eq!(t.cache.winners.len(), 1);
        assert!(t.cache.winners[0]
            .samples
            .iter()
            .all(|sample| sample.secs == 10));
        let _ = fs::remove_file(&t.path);
    }

    fn sample(hps: u64) -> Sample {
        Sample {
            hashes: hps * 30,
            secs: 30,
        }
    }

    fn snapshot() -> CpuAdaptiveSnapshot {
        CpuAdaptiveSnapshot {
            kernel: CpuKernel::preferred(),
            kernel_generation: 1,
            kernel_ready: true,
            backing_bytes: [0, 0, 0, CPU_LANE_MEMORY_BYTES, 0],
            running: true,
            threads: 1,
            committed_bytes: CPU_LANE_MEMORY_BYTES,
            resident_bytes: CPU_LANE_MEMORY_BYTES,
            hashes: 0,
            hashing: true,
            allocation_failures: 0,
            warmed: 1,
        }
    }

    fn tuner() -> Tuner {
        let mut cfg = super::super::tests::test_config();
        cfg.cpu_autotune_config_path = std::env::temp_dir().join(format!(
            "seine-kernel-test-{}-{:?}.json",
            std::process::id(),
            std::thread::current().id()
        ));
        let mut t = Tuner::identity_neutral(&cfg, CpuAutotuneHostFingerprint::default());
        t.cache.winners.clear();
        t.candidates.retain(|k| *k != CpuKernel::Avx512256Stream);
        // Independent of whether this test runner is the validated Ryzen.
        t.startup = None;
        t
    }

    #[test]
    fn native_constructor_uses_runtime_identity_in_hardware_tests() {
        let cfg = super::super::tests::test_config();
        let identity = crate::runtime_identity::cpu_identity();
        let supported: Vec<_> = CpuKernel::ALL
            .into_iter()
            .filter(|k| k.is_supported())
            .collect();
        let expected = candidates_for(&identity, &supported);
        let t = Tuner::new(&cfg, CpuAutotuneHostFingerprint::default());
        assert_eq!(t.candidates, expected);
        assert_eq!(t.startup, startup_kernel_for(&identity, &expected));
    }

    #[test]
    fn injected_identity_controls_candidates_startup_and_cache_fingerprint() {
        use crate::runtime_identity::CpuIdentity;
        let cfg = super::super::tests::test_config();
        let host = CpuAutotuneHostFingerprint::default();
        let neutral = Tuner::identity_neutral(&cfg, host.clone());
        assert_eq!(neutral.candidates, candidates());
        assert_eq!(neutral.startup, None);
        let turin = CpuIdentity {
            vendor: Some("AuthenticAMD".into()),
            family: Some(0x1a),
            model: Some(0x02),
            ..CpuIdentity::default()
        };
        for (identity, eligible, starts_streaming) in [
            (turin.clone(), true, false),
            (
                CpuIdentity {
                    model: Some(0x44),
                    ..turin.clone()
                },
                true,
                true,
            ),
            (
                CpuIdentity {
                    family: Some(0x19),
                    model: Some(0x11),
                    ..turin.clone()
                },
                true,
                false,
            ),
            (
                CpuIdentity {
                    vendor: Some("GenuineIntel".into()),
                    ..turin
                },
                false,
                false,
            ),
        ] {
            let t = Tuner::for_identity(&cfg, host.clone(), &identity);
            let streaming = eligible && CpuKernel::Avx512256Stream.is_supported();
            assert_eq!(
                t.candidates.contains(&CpuKernel::Avx512256Stream),
                streaming
            );
            assert_eq!(
                t.startup,
                (streaming && starts_streaming).then_some(CpuKernel::Avx512256Stream)
            );
            assert_eq!(
                t.cache.configuration != neutral.cache.configuration,
                streaming
            );
            assert!(t.candidates.iter().all(|k| k.is_supported()));
        }
    }

    #[test]
    fn candidates_are_supported_and_experimental_x86_path_stays_manual() {
        let paths = candidates();
        // Only the identity-gated streaming path may add a third candidate.
        let streaming = usize::from(paths.contains(&CpuKernel::Avx512256Stream));
        assert!(paths.len() <= 2 + streaming);
        assert!(paths.iter().all(|path| path.is_supported()));
        assert!(!paths.contains(&CpuKernel::Avx512256));
        assert_eq!(
            paths.contains(&CpuKernel::NeonSha3),
            CpuKernel::NeonSha3.is_supported()
        );
    }

    #[test]
    fn noise_and_low_hash_count_cannot_promote_kernel() {
        assert!(improves(sample(100), sample(110), sample(100)));
        assert!(!improves(sample(100), sample(102), sample(100)));
        assert!(!improves(sample(100), sample(120), sample(110)));
        assert!(!improves(
            Sample {
                hashes: 1,
                secs: 30
            },
            Sample {
                hashes: 2,
                secs: 30
            },
            Sample {
                hashes: 1,
                secs: 30
            }
        ));
    }

    #[test]
    fn two_confirmations_and_switch_acknowledgements_are_required() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let mut s = snapshot();
        let challenger = candidates().into_iter().find(|&k| k != s.kernel).unwrap();
        let mut now = 0;
        assert!(t.tick(now, &[s], true, true).hold_counts);
        for (index, rate) in [100, 110, 100, 100, 110, 100].into_iter().enumerate() {
            now += 1;
            s.kernel_ready = false;
            assert!(t.tick(now, &[s], true, true).hold_counts);
            assert!(t.trial.as_ref().unwrap().window.is_none());
            s.kernel_ready = true;
            t.tick(now, &[s], true, true);
            now += 30;
            s.hashes += rate * 30;
            let action = t.tick(now, &[s], true, true);
            if let Some(kernel) = action.kernel {
                s.kernel = kernel;
                s.kernel_generation += 1;
            }
            if index < 5 {
                assert!(t.cache.winners.is_empty());
            }
        }
        assert_eq!(s.kernel, challenger);
        assert_eq!(t.cache.winners.len(), 1);
        assert!(!t.tick(now + 1, &[s], true, true).hold_counts);
        assert!(!t.tick(now + 2, &[s], true, true).hold_counts);
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn noisy_second_confirmation_is_not_cached_as_a_loss() {
        if candidates().len() < 2 {
            return;
        }
        for (rates, conclusive) in [
            ([100, 110, 100, 100, 120, 110], false),
            ([100, 110, 100, 100, 95, 100], true),
        ] {
            let mut t = tuner();
            let mut s = snapshot();
            let base = s.kernel;
            let mut now = 0;
            assert!(t.tick(now, &[s], true, true).hold_counts);
            for rate in rates {
                now += 1;
                t.tick(now, &[s], true, true);
                now += 30;
                s.hashes += rate * 30;
                let action = t.tick(now, &[s], true, true);
                if let Some(kernel) = action.kernel {
                    s.kernel = kernel;
                    s.kernel_generation += 1;
                }
            }
            assert_eq!(s.kernel, base);
            assert_eq!(t.cache.winners.len(), usize::from(conclusive));
            assert_eq!(
                t.next_check,
                now + if conclusive { RECHECK_SECS } else { RETRY_SECS }
            );
            assert!(!t.tick(now + 1, &[s], true, true).hold_counts);
            let _ = fs::remove_file(&t.path);
        }
    }

    #[test]
    fn low_count_timeout_in_new_context_does_not_inherit_old_recheck() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let mut s = snapshot();
        t.checked = Some(Context::from_snapshots(&[s]));
        t.next_check = RECHECK_SECS;
        s.threads = 2;
        s.warmed = 2;
        s.committed_bytes *= 2;
        s.resident_bytes *= 2;
        s.backing_bytes[3] *= 2;
        assert!(t.tick(1, &[s], true, true).hold_counts);
        t.tick(2, &[s], true, true);
        s.hashes = 31;
        assert!(t.tick(MAX_TRIAL_SECS - 1, &[s], true, true).hold_counts);
        assert!(t.trial.as_ref().unwrap().samples.is_empty());
        let now = MAX_TRIAL_SECS + 1;
        assert_eq!(t.tick(now, &[s], true, true).kernel, Some(s.kernel));
        assert!(t.trial.is_none());
        assert!(t.cache.winners.is_empty());
        assert_eq!(t.next_check, now + RETRY_SECS);
        assert!(!t.tick(now + RETRY_SECS - 1, &[s], true, true).hold_counts);
        assert!(t.tick(now + RETRY_SECS, &[s], true, true).hold_counts);
    }

    #[test]
    fn interrupts_and_changed_backing_restore_baseline_and_back_off() {
        if candidates().len() < 2 {
            return;
        }
        for backing_change in [true, false] {
            let mut t = tuner();
            let mut s = snapshot();
            t.tick(0, &[s], true, true);
            t.tick(1, &[s], true, true);
            s.hashes = 3000;
            let action = t.tick(31, &[s], true, true);
            s.kernel = action.kernel.unwrap();
            if backing_change {
                s.backing_bytes = [CPU_LANE_MEMORY_BYTES, 0, 0, 0, 0];
            } else {
                t.tick(32, &[s], false, true);
            }
            let action = t.tick(35, &[s], backing_change, true);
            assert_eq!(action.kernel, Some(CpuKernel::preferred()));
            assert!(t.trial.is_none());
            assert!(t.cache.winners.is_empty());
            assert!(!t.tick(36, &[s], true, true).hold_counts);
        }
    }

    #[test]
    fn cache_is_scoped_to_count_backing_host_build_and_supported_paths() {
        let host = CpuAutotuneHostFingerprint::default();
        let context = Context::from_snapshots(&[snapshot()]);
        let mut cache = Cache {
            schema: CACHE_SCHEMA,
            host: host.clone(),
            configuration: "test".into(),
            winners: vec![Winner {
                context: context.clone(),
                kernel: CpuKernel::preferred().to_string(),
                base: CpuKernel::preferred().to_string(),
                candidate: "avx2".into(),
                samples: vec![sample(100); 3],
                timestamp: 100,
            }],
        };
        assert!(cache.compatible(&host, "test"));
        cache.schema = 1;
        assert!(!cache.compatible(&host, "test"));
        cache.schema = CACHE_SCHEMA;
        assert!(cache.compatible(&host, "test"));
        let mut other = host.clone();
        other.build_fingerprint = "changed".into();
        assert!(!cache.compatible(&other, "test"));
        other = host.clone();
        other.affinity_topology = "changed".into();
        assert!(!cache.compatible(&other, "test"));
        assert!(!cache.compatible(&host, "other"));
        let mut changed = context.clone();
        changed.workers[0] += 1;
        assert!(cache.winner(&changed, 100, &candidates()).is_none());
        changed = context.clone();
        changed.backing[0].swap(0, 3);
        assert!(cache.winner(&changed, 100, &candidates()).is_none());
        assert!(cache.winner(&context, 99, &candidates()).is_none());
        assert!(cache
            .winner(
                &context,
                100 + CPU_AUTOTUNE_RECORD_MAX_AGE_SECS,
                &candidates()
            )
            .is_none());
        assert_eq!(
            cache.winner(&context, 100, &candidates()),
            Some(CpuKernel::preferred())
        );
        cache.winners[0].samples = [100, 110, 100, 100, 120, 110]
            .into_iter()
            .map(sample)
            .collect();
        assert!(cache.winner(&context, 100, &candidates()).is_none());
        cache.winners[0].samples = [100, 110, 100, 100, 95, 100]
            .into_iter()
            .map(sample)
            .collect();
        assert_eq!(
            cache.winner(&context, 100, &candidates()),
            Some(CpuKernel::preferred())
        );
        cache.winners[0].kernel = "avx512-256".into();
        assert!(cache.winner(&context, 100, &candidates()).is_none());
    }

    #[test]
    fn count_probe_blocks_kernel_probe_and_trial_has_hard_deadline() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let s = snapshot();
        assert!(!t.tick(0, &[s], true, false).hold_counts);
        assert!(t.trial.is_none());
        assert!(t.tick(1, &[s], true, true).hold_counts);
        let action = t.tick(1 + MAX_TRIAL_SECS, &[s], true, true);
        assert_eq!(action.kernel, Some(CpuKernel::preferred()));
        assert!(t.trial.is_none());
    }
    #[test]
    fn streaming_trials_require_validated_identity_and_supported_instructions() {
        use crate::runtime_identity::CpuIdentity;
        let supported = [
            CpuKernel::Avx512,
            CpuKernel::Avx2,
            CpuKernel::Avx512256Stream,
        ];
        let turin = CpuIdentity {
            vendor: Some("AuthenticAMD".into()),
            family: Some(26),
            model: Some(2),
            stepping: Some(1),
        };
        assert_eq!(
            candidates_for(&turin, &supported),
            [
                CpuKernel::Avx512,
                CpuKernel::Avx512256Stream,
                CpuKernel::Avx2
            ]
        );
        assert_eq!(candidates_for(&turin, &supported[..2]), supported[..2]);
        let ryzen = CpuIdentity {
            model: Some(0x44),
            ..turin.clone()
        };
        assert_eq!(candidates_for(&ryzen, &supported), supported);
        assert_eq!(candidates_for(&ryzen, &supported[..2]), supported[..2]);
        let genoa = CpuIdentity {
            family: Some(0x19),
            model: Some(0x11),
            ..turin.clone()
        };
        assert_eq!(candidates_for(&genoa, &supported), supported);
        assert_eq!(candidates_for(&genoa, &supported[..2]), supported[..2]);
        assert_eq!(startup_kernel_for(&genoa, &supported), None);
        for identity in [
            CpuIdentity {
                vendor: Some("GenuineIntel".into()),
                ..turin.clone()
            },
            CpuIdentity {
                family: Some(25),
                model: Some(0x10),
                ..turin.clone()
            },
            CpuIdentity {
                family: Some(25),
                model: Some(0x12),
                ..turin.clone()
            },
            CpuIdentity {
                model: Some(0x70),
                ..turin.clone()
            },
            CpuIdentity::default(),
        ] {
            assert_eq!(candidates_for(&identity, &supported), supported[..2]);
        }
        assert_eq!(
            candidates_for(&turin, &[CpuKernel::Avx2]),
            [CpuKernel::Avx2]
        );
    }

    fn three_path_tuner() -> Tuner {
        let mut t = tuner();
        // Simulate eligible host paths, independent of this test runner's ISA.
        t.candidates = vec![
            CpuKernel::Avx512,
            CpuKernel::Avx2,
            CpuKernel::Avx512256Stream,
        ];
        t
    }

    fn run_comparison(
        t: &mut Tuner,
        s: &mut CpuAdaptiveSnapshot,
        now: &mut u64,
        rates: &[u64],
    ) -> Action {
        *now += 1;
        // A previously promoted path must settle before the next comparison.
        if t.settling.is_some() {
            let action = t.tick(*now, &[*s], true, true);
            assert_eq!(action.hold_counts, !t.pending.is_empty());
            *now += 1;
        }
        assert!(t.tick(*now, &[*s], true, true).hold_counts);
        let mut action = Action::default();
        for rate in rates {
            *now += 1;
            t.tick(*now, &[*s], true, true);
            *now += 30;
            s.hashes += rate * 30;
            action = t.tick(*now, &[*s], true, true);
            if let Some(kernel) = action.kernel {
                s.kernel = kernel;
                s.kernel_generation += 1;
            }
        }
        action
    }

    #[test]
    fn turin_streaming_first_still_confirms_twice_and_checks_avx2_before_caching() {
        let mut t = three_path_tuner();
        t.candidates = candidates_for(
            &crate::runtime_identity::CpuIdentity {
                vendor: Some("AuthenticAMD".into()),
                family: Some(0x1a),
                model: Some(0x02),
                stepping: Some(1),
            },
            &t.candidates,
        );
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        run_comparison(&mut t, &mut s, &mut now, &[100, 125, 100]);
        let trial = t
            .trial
            .as_ref()
            .expect("second confirmation remains required");
        assert_eq!(trial.base, CpuKernel::Avx512);
        assert_eq!(trial.candidate, CpuKernel::Avx512256Stream);
        assert_eq!(trial.samples.len(), 3);
        assert!(t.cache.winners.is_empty());
        // Complete the same active trial without starting a new comparison.
        for rate in [100, 125, 100] {
            now += 1;
            t.tick(now, &[s], true, true);
            now += 30;
            s.hashes += rate * 30;
            if let Some(kernel) = t.tick(now, &[s], true, true).kernel {
                s.kernel = kernel;
                s.kernel_generation += 1;
            }
        }
        assert_eq!(s.kernel, CpuKernel::Avx512256Stream);
        assert_eq!(t.pending, [CpuKernel::Avx2]);
        assert!(t.cache.winners.is_empty());
        run_comparison(&mut t, &mut s, &mut now, &[125, 95, 125]);
        assert_eq!(t.cache.winners.len(), 1);
        assert_eq!(t.cache.winners[0].kernel, "avx512-256-stream");
        assert_eq!(t.cache.winners[0].candidate, "avx2");
        assert!(t.pending.is_empty());
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn streaming_startup_requires_validated_ryzen_identity_and_candidate() {
        use crate::runtime_identity::CpuIdentity;
        let ryzen = CpuIdentity {
            vendor: Some("AuthenticAMD".into()),
            family: Some(0x1a),
            model: Some(0x44),
            ..CpuIdentity::default()
        };
        let all = [
            CpuKernel::Avx512,
            CpuKernel::Avx2,
            CpuKernel::Avx512256Stream,
        ];
        assert_eq!(
            startup_kernel_for(&ryzen, &all),
            Some(CpuKernel::Avx512256Stream)
        );
        assert_eq!(startup_kernel_for(&ryzen, &all[..2]), None);
        for other in [
            CpuIdentity {
                model: Some(0x02),
                ..ryzen.clone()
            },
            CpuIdentity {
                family: Some(0x19),
                ..ryzen.clone()
            },
            CpuIdentity {
                vendor: Some("GenuineIntel".into()),
                ..ryzen.clone()
            },
            CpuIdentity::default(),
        ] {
            assert_eq!(startup_kernel_for(&other, &all), None);
        }
    }

    #[test]
    fn validated_startup_path_is_compared_against_others_from_eight_workers() {
        let mut t = three_path_tuner();
        t.startup = Some(CpuKernel::Avx512256Stream);
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        s.threads = 4;
        // Below the validated range, start comparisons on the default path.
        let a = t.tick(1, &[s], true, true);
        assert_eq!(a.kernel, None);
        assert_eq!(t.trial.as_ref().map(|t| t.base), Some(CpuKernel::Avx512));

        let mut t = three_path_tuner();
        t.startup = Some(CpuKernel::Avx512256Stream);
        s.threads = 8;
        let a = t.tick(1, &[s], true, true);
        assert_eq!(a.kernel, Some(CpuKernel::Avx512256Stream));
        assert!(a.hold_counts && a.reset_scores);
        assert!(t.cache.winners.is_empty());
        s.kernel = CpuKernel::Avx512256Stream;
        s.kernel_generation += 1;
        let mut now = 2;
        // Settles, then compares the remaining paths against streaming at once.
        let a = run_comparison(&mut t, &mut s, &mut now, &[100, 95, 100]);
        assert_eq!(s.kernel, CpuKernel::Avx512256Stream);
        assert!(a
            .message
            .unwrap()
            .contains("avx512-256-stream 100.00 / avx512 95.00"));
        run_comparison(&mut t, &mut s, &mut now, &[100, 90, 100]);
        assert_eq!(s.kernel, CpuKernel::Avx512256Stream);
        assert_eq!(t.cache.winners.len(), 1);
        assert_eq!(t.cache.winners[0].kernel, "avx512-256-stream");
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn drifted_baseline_is_reported_separately_from_no_gain() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        let a = run_comparison(&mut t, &mut s, &mut now, &[100, 130, 90]);
        let message = a.message.unwrap();
        assert!(
            message.starts_with("keeping current kernel; baseline drifted"),
            "{message}"
        );
        assert!(
            message.contains("avx512 100.00 / avx2 130.00 / avx512 90.00"),
            "{message}"
        );
        assert!(t.cache.winners.is_empty());
        assert_eq!(t.next_check, now + RETRY_SECS);
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn third_path_is_reached_after_a_loss_and_cached_only_after_confirmation() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        let a = run_comparison(&mut t, &mut s, &mut now, &[100, 95, 100]);
        assert!(a.hold_counts);
        assert_eq!(t.pending, [CpuKernel::Avx512256Stream]);
        assert!(t.cache.winners.is_empty());
        run_comparison(&mut t, &mut s, &mut now, &[100, 125, 100, 100, 125, 100]);
        assert_eq!(s.kernel, CpuKernel::Avx512256Stream);
        assert_eq!(t.cache.winners.len(), 1);
        let context = Context::from_snapshots(&[s]);
        assert_eq!(
            t.cache.winner(&context, unix_secs(), &t.candidates),
            Some(s.kernel)
        );
        assert_eq!(t.next_check, now + RECHECK_SECS);
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn next_challenger_uses_the_promoted_incumbent_and_keeps_it_if_faster() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        run_comparison(&mut t, &mut s, &mut now, &[100, 110, 100, 100, 110, 100]);
        assert_eq!(s.kernel, CpuKernel::Avx2);
        assert!(t.cache.winners.is_empty());
        run_comparison(&mut t, &mut s, &mut now, &[110, 105, 110]);
        assert_eq!(s.kernel, CpuKernel::Avx2);
        assert_eq!(t.cache.winners.len(), 1);
        assert_eq!(t.cache.winners[0].base, "avx2");
        assert_eq!(t.cache.winners[0].candidate, "avx512-256-stream");
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn changed_context_discards_pending_challengers_and_cannot_reuse_streaming_winner() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        run_comparison(&mut t, &mut s, &mut now, &[100, 95, 100]);
        s.backing_bytes.swap(0, 3);
        t.tick(now + 1, &[s], true, true);
        assert_eq!(t.trial.as_ref().unwrap().candidate, CpuKernel::Avx2);
        assert!(t.cache.winners.is_empty());
        t.abort(now + 2);
        assert!(t.pending.is_empty());
    }

    #[test]
    fn a_streaming_winner_can_switch_back_when_the_worker_count_changes() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        s.threads = 24;
        s.warmed = 24;
        s.backing_bytes[3] = 24 * CPU_LANE_MEMORY_BYTES;
        s.resident_bytes = s.backing_bytes[3];
        s.committed_bytes = s.resident_bytes;
        let mut now = 0;
        run_comparison(&mut t, &mut s, &mut now, &[100, 95, 100]);
        run_comparison(&mut t, &mut s, &mut now, &[100, 125, 100, 100, 125, 100]);
        assert_eq!(s.kernel, CpuKernel::Avx512256Stream);
        assert_eq!(t.cache.winners.len(), 1);
        s.threads = 1;
        s.warmed = 1;
        s.backing_bytes[3] = CPU_LANE_MEMORY_BYTES;
        s.resident_bytes = s.backing_bytes[3];
        s.committed_bytes = s.resident_bytes;
        run_comparison(&mut t, &mut s, &mut now, &[100, 110, 100, 100, 110, 100]);
        assert_eq!(s.kernel, CpuKernel::Avx512);
        run_comparison(&mut t, &mut s, &mut now, &[110, 105, 110]);
        assert_eq!(s.kernel, CpuKernel::Avx512);
        assert!(t.pending.is_empty());
        let _ = fs::remove_file(&t.path);
    }

    #[test]
    fn noisy_third_path_does_not_cache_a_partial_sweep() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        run_comparison(&mut t, &mut s, &mut now, &[100, 110, 100, 100, 110, 100]);
        run_comparison(&mut t, &mut s, &mut now, &[110, 130, 125]);
        assert_eq!(s.kernel, CpuKernel::Avx2);
        assert!(t.cache.winners.is_empty());
        assert!(t.pending.is_empty());
        assert_eq!(t.next_check, now + RETRY_SECS);
        assert!(!t.tick(now + RETRY_SECS - 1, &[s], true, true).hold_counts);
        assert!(t.tick(now + RETRY_SECS, &[s], true, true).hold_counts);
    }
    #[test]
    #[ignore = "24 real 2 GiB workers with reserved local HugeTLB on validated EPYC; up to 15 minutes"]
    fn epyc_streaming_productive_selection() {
        use crate::backend::cpu::{CpuBackend, CpuBackendTuning};
        use crate::backend::{NonceChunk, PowBackend, WorkAssignment, WorkTemplate};
        use std::sync::Arc;
        use std::time::{Duration, Instant};
        let identity = crate::runtime_identity::cpu_identity();
        assert!(
            identity.vendor.as_deref() == Some("AuthenticAMD")
                && identity.family == Some(0x1a)
                && identity.model == Some(0x02),
            "requires validated EPYC identity; do not allocate 24 arenas on a desktop"
        );
        let mut cfg = super::super::tests::test_config();
        cfg.cpu_autotune_config_path =
            std::env::temp_dir().join(format!("seine-epyc-productive-{}", std::process::id()));
        cfg.cpu_autotune_secs = 6;
        let mut t = Tuner::new(&cfg, cpu_autotune_host_fingerprint());
        assert!(
            t.candidates.contains(&CpuKernel::Avx512256Stream),
            "requires runtime support for the streaming kernel"
        );
        t.cache.winners.clear();
        let backend = CpuBackend::adaptive(
            24,
            24,
            crate::config::CpuAffinityMode::Auto,
            CpuBackendTuning {
                page_mode: crate::config::CpuPageMode::Large,
                ..CpuBackendTuning::default()
            },
        );
        backend.start().unwrap();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let started = Instant::now();
            let budget = Duration::from_secs(900);
            backend
                .assign_work(WorkAssignment {
                    template: Arc::new(WorkTemplate {
                        work_id: 1,
                        epoch: 1,
                        header_base: Arc::from(vec![0u8; blocknet_pow_spec::POW_HEADER_BASE_LEN]),
                        target: [0; 32],
                        dynamic_share_target: None,
                        pause_on_solution: false,
                        stop_at: started + budget,
                    }),
                    nonce_chunk: NonceChunk {
                        start_nonce: 0,
                        nonce_count: 1_000_000,
                    },
                })
                .unwrap();
            loop {
                assert!(
                    started.elapsed() < budget,
                    "automatic streaming comparison did not finish"
                );
                let snapshot = backend.adaptive_snapshot();
                assert_eq!(snapshot.allocation_failures, 0);
                let ready = snapshot.hashing
                    && snapshot.warmed == 24
                    && snapshot.resident_bytes == 24 * CPU_LANE_MEMORY_BYTES;
                let action = t.tick(started.elapsed().as_secs(), &[snapshot], ready, true);
                if let Some(message) = action.message {
                    println!("{message}");
                }
                if let Some(kernel) = action.kernel {
                    backend.set_active_kernel(kernel).unwrap();
                }
                if !t.cache.winners.is_empty() && snapshot.kernel_ready && t.settling.is_none() {
                    assert_eq!(snapshot.kernel, CpuKernel::Avx512256Stream);
                    assert_eq!(snapshot.backing_bytes[0], 24 * CPU_LANE_MEMORY_BYTES);
                    assert!(snapshot.hashes > 0);
                    assert_eq!(
                        t.cache.winner(
                            &Context::from_snapshots(&[snapshot]),
                            unix_secs(),
                            &t.candidates
                        ),
                        Some(snapshot.kernel)
                    );
                    println!(
                        "EPYC_PRODUCTIVE_PASS hashes={} kernel={} workers={} backing={:?}",
                        snapshot.hashes, snapshot.kernel, snapshot.threads, snapshot.backing_bytes
                    );
                    println!(
                        "EPYC_COMPARISON {}",
                        serde_json::to_string(&t.cache.winners[0]).unwrap()
                    );
                    break;
                }
                std::thread::sleep(Duration::from_secs(1));
            }
        }));
        backend.stop();
        let _ = fs::remove_file(&t.path);
        assert_eq!(backend.adaptive_snapshot().resident_bytes, 0);
        result.unwrap();
    }
    #[test]
    fn aborted_count_does_not_delay_a_different_count_or_forget_its_own_backoff() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let mut first = snapshot();
        first.threads = 9;
        first.warmed = 9;
        first.committed_bytes = 9 * CPU_LANE_MEMORY_BYTES;
        first.resident_bytes = first.committed_bytes;
        first.backing_bytes[3] = first.committed_bytes;
        assert!(t.tick(0, &[first], true, true).hold_counts);
        t.abort(10);
        let mut second = first;
        second.threads = 12;
        second.warmed = 12;
        second.committed_bytes = 12 * CPU_LANE_MEMORY_BYTES;
        second.resident_bytes = second.committed_bytes;
        second.backing_bytes[3] = second.committed_bytes;
        assert!(
            t.tick(11, &[second], true, true).hold_counts,
            "a new count must compare kernels before count selection"
        );
        t.abort(12);
        assert!(!t.tick(13, &[first], true, true).hold_counts);
        // Changing backing at the interrupted count must not evade its backoff.
        first.backing_bytes = [first.resident_bytes, 0, 0, 0, 0];
        assert!(!t.tick(14, &[first], true, true).hold_counts);
        assert!(t.tick(10 + RETRY_SECS, &[first], true, true).hold_counts);
    }

    #[test]
    fn idle_abort_does_not_extend_last_checked_counts_retry() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let s = snapshot();
        assert!(t.tick(0, &[s], true, true).hold_counts);
        t.abort(1);
        t.abort(100);
        assert!(t.tick(301, &[s], true, true).hold_counts);
    }

    #[test]
    fn inconclusive_count_keeps_backoff_after_another_count_is_visited() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let mut first = snapshot();
        let mut now = 0;
        assert!(t.tick(now, &[first], true, true).hold_counts);
        for rate in [100, 120, 110] {
            now += 1;
            t.tick(now, &[first], true, true);
            now += 30;
            first.hashes += rate * 30;
            if let Some(kernel) = t.tick(now, &[first], true, true).kernel {
                first.kernel = kernel;
                first.kernel_generation += 1;
            }
        }
        assert!(t.trial.is_none());
        assert!(t.cache.winners.is_empty(), "drift is not a cached loss");
        let retry = now + RETRY_SECS;
        let mut second = first;
        second.threads = 2;
        second.warmed = 2;
        second.committed_bytes *= 2;
        second.resident_bytes *= 2;
        second.backing_bytes[3] *= 2;
        assert!(t.tick(now + 1, &[second], true, true).hold_counts);
        t.abort(now + 2);
        assert!(!t.tick(now + 3, &[first], true, true).hold_counts);
        assert!(t.tick(retry, &[first], true, true).hold_counts);
    }

    #[test]
    fn stopped_backend_does_not_block_acknowledgements_or_contribute_hashes() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let mut s = snapshot();
        let mut stopped = s;
        stopped.running = false;
        stopped.hashing = false;
        stopped.kernel_ready = false;
        stopped.hashes = 1_000_000;
        assert!(t.tick(0, &[stopped, s], true, true).hold_counts);
        assert!(t.tick(1, &[stopped, s], true, true).hold_counts);
        s.hashes = 3000;
        stopped.hashes += 50_000;
        let action = t.tick(31, &[stopped, s], true, true);
        assert!(action.kernel.is_some());
        let trial = t.trial.as_ref().unwrap();
        assert_eq!(trial.context.members, vec![1]);
        assert_eq!(trial.context.workers, vec![1]);
        assert_eq!(trial.samples[0].hashes, 3000);
        assert_eq!(trial.samples[0].secs, 30);
    }

    #[test]
    fn cache_is_scoped_to_members_count_backing_host_build_and_supported_paths() {
        let host = CpuAutotuneHostFingerprint::default();
        let context = Context::from_snapshots(&[snapshot()]);
        let mut cache = Cache {
            schema: CACHE_SCHEMA,
            host: host.clone(),
            configuration: "test".into(),
            winners: vec![Winner {
                context: context.clone(),
                kernel: CpuKernel::preferred().to_string(),
                base: CpuKernel::preferred().to_string(),
                candidate: "avx2".into(),
                samples: vec![sample(100); 3],
                timestamp: 100,
            }],
        };
        assert!(cache.compatible(&host, "test"));
        cache.schema = 1;
        assert!(!cache.compatible(&host, "test"));
        cache.schema = CACHE_SCHEMA;
        assert!(cache.compatible(&host, "test"));
        let mut other = host.clone();
        other.build_fingerprint = "changed".into();
        assert!(!cache.compatible(&other, "test"));
        other = host.clone();
        other.affinity_topology = "changed".into();
        assert!(!cache.compatible(&other, "test"));
        assert!(!cache.compatible(&host, "other"));
        let mut changed = context.clone();
        changed.members[0] = 1;
        assert!(cache.winner(&changed, 100, &candidates()).is_none());
        changed = context.clone();
        changed.workers[0] += 1;
        assert!(cache.winner(&changed, 100, &candidates()).is_none());
        changed = context.clone();
        changed.backing[0].swap(0, 3);
        assert!(cache.winner(&changed, 100, &candidates()).is_none());
        assert!(cache.winner(&context, 99, &candidates()).is_none());
        assert!(cache
            .winner(
                &context,
                100 + CPU_AUTOTUNE_RECORD_MAX_AGE_SECS,
                &candidates()
            )
            .is_none());
        assert_eq!(
            cache.winner(&context, 100, &candidates()),
            Some(CpuKernel::preferred())
        );
        cache.winners[0].samples = [100, 110, 100, 100, 120, 110]
            .into_iter()
            .map(sample)
            .collect();
        assert!(cache.winner(&context, 100, &candidates()).is_none());
        cache.winners[0].samples = [100, 110, 100, 100, 95, 100]
            .into_iter()
            .map(sample)
            .collect();
        assert_eq!(
            cache.winner(&context, 100, &candidates()),
            Some(CpuKernel::preferred())
        );
        cache.winners[0].kernel = "avx512-256".into();
        assert!(cache.winner(&context, 100, &candidates()).is_none());
    }

    #[test]
    fn caller_can_block_new_kernel_probe_and_trial_has_hard_deadline() {
        if candidates().len() < 2 {
            return;
        }
        let mut t = tuner();
        let s = snapshot();
        assert!(!t.tick(0, &[s], true, false).hold_counts);
        assert!(t.trial.is_none());
        assert!(t.tick(1, &[s], true, true).hold_counts);
        let action = t.tick(1 + MAX_TRIAL_SECS, &[s], true, true);
        assert_eq!(action.kernel, Some(CpuKernel::preferred()));
        assert!(t.trial.is_none());
    }
    #[test]
    fn abort_between_challengers_backs_off_only_that_count() {
        let mut t = three_path_tuner();
        let mut s = snapshot();
        s.kernel = CpuKernel::Avx512;
        let mut now = 0;
        run_comparison(&mut t, &mut s, &mut now, &[100, 95, 100]);
        assert!(t.is_comparing() && t.trial.is_none());
        assert!(t.abort(now + 1).interrupted);
        assert!(t.pending.is_empty() && t.cache.winners.is_empty());
        assert!(t.retry_pending(now + 2, &[s]));
        s.threads += 1;
        s.warmed += 1;
        assert!(t.tick(now + 2, &[s], true, true).hold_counts);
        let _ = fs::remove_file(t.path);
    }
}
