//! Fresh allowlisted placement inputs for telemetry, never the startup cache.
#[cfg(any(target_os = "linux", target_os = "windows", test))]
use sha3::{Digest, Sha3_256};
#[cfg(any(target_os = "linux", target_os = "windows", test))]
use std::collections::BTreeSet;
use std::time::{Duration, Instant};

#[cfg(any(target_os = "linux", target_os = "windows", test))]
const MAX_CPUS: usize = 512;
const SLOW_PROBE: Duration = Duration::from_millis(25);
const RETRY_DELAY: Duration = Duration::from_secs(30);

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct Placement {
    pub allowed_logical_cpus: Option<u32>,
    pub fingerprint: Option<String>,
}

pub(crate) struct PlacementSampler {
    probe: fn() -> Placement,
    retry_after: Option<Instant>,
}

impl Default for PlacementSampler {
    fn default() -> Self {
        Self {
            probe: measure,
            retry_after: None,
        }
    }
}

impl PlacementSampler {
    pub(crate) fn sample(&mut self) -> Placement {
        let now = Instant::now();
        if self.retry_after.is_some_and(|next| now < next) {
            return Placement::default();
        }
        let result = (self.probe)();
        let finished = Instant::now();
        self.accept(result, now, finished)
    }

    fn accept(&mut self, result: Placement, started: Instant, finished: Instant) -> Placement {
        if finished.duration_since(started) > SLOW_PROBE {
            // No stale last-good value during backoff. This suppresses hints,
            // not mining, and avoids repeatedly slow metadata reads.
            self.retry_after = Some(finished + RETRY_DELAY);
            Placement::default()
        } else {
            self.retry_after = None;
            result
        }
    }

    #[cfg(test)]
    pub(crate) fn with_probe(probe: fn() -> Placement) -> Self {
        Self {
            probe,
            retry_after: None,
        }
    }
}

#[cfg(any(target_os = "linux", target_os = "windows"))]
fn allowed_cpus() -> Option<BTreeSet<usize>> {
    let ids: BTreeSet<_> = core_affinity::get_core_ids()?
        .into_iter()
        .map(|cpu| cpu.id)
        .collect();
    (!ids.is_empty() && ids.len() <= MAX_CPUS).then_some(ids)
}

#[cfg(any(target_os = "linux", target_os = "windows", test))]
fn measured_from(
    before: Option<BTreeSet<usize>>,
    inputs: Option<String>,
    after: Option<BTreeSet<usize>>,
) -> Placement {
    let Some(before) = before.filter(|mask| !mask.is_empty() && mask.len() <= MAX_CPUS) else {
        return Placement::default();
    };
    if after.as_ref() != Some(&before) {
        return Placement::default();
    }
    Placement {
        allowed_logical_cpus: Some(before.len() as u32),
        fingerprint: inputs.map(|inputs| {
            hex::encode(Sha3_256::digest(format!(
                "seine-placement-v1:{before:?}:{inputs}"
            )))
        }),
    }
}

fn measure() -> Placement {
    #[cfg(any(target_os = "linux", target_os = "windows"))]
    {
        let before = allowed_cpus();
        let inputs = before.as_ref().and_then(|allowed| {
            #[cfg(target_os = "linux")]
            {
                super::topology::measured_inputs(allowed).map(|s| format!("linux:{s}"))
            }
            #[cfg(target_os = "windows")]
            {
                windows_inputs(allowed)
            }
        });
        measured_from(before, inputs, allowed_cpus())
    }
    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    Placement::default()
}

#[cfg(any(target_os = "windows", test))]
fn complete_groups(allowed: &BTreeSet<usize>, groups: &mut [Vec<usize>]) -> bool {
    let mut seen = BTreeSet::new();
    for group in groups.iter_mut() {
        group.sort_unstable();
        if group.is_empty()
            || group
                .iter()
                .any(|id| !allowed.contains(id) || !seen.insert(*id))
        {
            return false;
        }
    }
    groups.sort_unstable();
    seen == *allowed
}

#[cfg(any(target_os = "windows", test))]
fn complete_domains(
    allowed: &BTreeSet<usize>,
    cores: &mut [Vec<usize>],
    nodes: &mut [Vec<usize>],
    caches: &mut [Vec<usize>],
) -> bool {
    complete_groups(allowed, cores)
        && complete_groups(allowed, nodes)
        && complete_groups(allowed, caches)
        && cores.iter().all(|core| {
            [nodes.as_ref(), caches.as_ref()]
                .into_iter()
                .all(|domains: &[Vec<usize>]| {
                    domains
                        .iter()
                        .any(|group| core.iter().all(|cpu| group.contains(cpu)))
                })
        })
}

#[cfg(target_os = "windows")]
fn windows_inputs(allowed: &BTreeSet<usize>) -> Option<String> {
    use std::mem::{size_of, MaybeUninit};
    use std::ptr;
    use windows_sys::Win32::System::SystemInformation::{
        CacheUnified, GetLogicalProcessorInformation, RelationCache, RelationNumaNode,
        RelationProcessorCore, SYSTEM_LOGICAL_PROCESSOR_INFORMATION,
    };
    use windows_sys::Win32::System::Threading::GetActiveProcessorGroupCount;
    // The existing affinity API uses one usize mask. Do not claim full topology
    // on multi-group Windows hosts until group-aware observations are available.
    if unsafe { GetActiveProcessorGroupCount() } != 1 {
        return None;
    }
    let mut bytes = 0;
    unsafe {
        let _ = GetLogicalProcessorInformation(ptr::null_mut(), &mut bytes);
    }
    let size = size_of::<SYSTEM_LOGICAL_PROCESSOR_INFORMATION>();
    if bytes == 0 || bytes as usize > 1024 * 1024 || bytes as usize % size != 0 {
        return None;
    }
    let count = bytes as usize / size;
    let mut entries = vec![MaybeUninit::<SYSTEM_LOGICAL_PROCESSOR_INFORMATION>::uninit(); count];
    if unsafe { GetLogicalProcessorInformation(entries.as_mut_ptr().cast(), &mut bytes) } == 0
        || bytes as usize > count * size
        || bytes as usize % size != 0
    {
        return None;
    }
    let (mut cores, mut nodes, mut caches) = (Vec::new(), Vec::new(), Vec::new());
    for entry in &entries[..bytes as usize / size] {
        let entry = unsafe { entry.assume_init_ref() };
        let group = allowed
            .iter()
            .copied()
            .filter(|id| *id < usize::BITS as usize && entry.ProcessorMask & (1usize << id) != 0)
            .collect::<Vec<_>>();
        if group.is_empty() {
            continue;
        }
        if entry.Relationship == RelationProcessorCore {
            cores.push(group);
        } else if entry.Relationship == RelationNumaNode {
            nodes.push(group);
        } else if entry.Relationship == RelationCache {
            let cache = unsafe { entry.Anonymous.Cache };
            if cache.Level == 3 && cache.Type == CacheUnified {
                caches.push(group);
            }
        }
    }
    if unsafe { GetActiveProcessorGroupCount() } != 1
        || !complete_domains(allowed, &mut cores, &mut nodes, &mut caches)
    {
        return None;
    }
    Some(format!("windows:{cores:?}:{nodes:?}:{caches:?}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn changing_unknown_and_oversized_masks_never_reuse_known_context() {
        let a = BTreeSet::from([0, 2]);
        let b = BTreeSet::from([1, 3]);
        let known = measured_from(
            Some(a.clone()),
            Some("fixture topology".into()),
            Some(a.clone()),
        );
        assert_eq!(known.allowed_logical_cpus, Some(2));
        assert_eq!(known.fingerprint.as_ref().unwrap().len(), 64);
        let other = measured_from(
            Some(b.clone()),
            Some("fixture topology".into()),
            Some(b.clone()),
        );
        assert_ne!(known.fingerprint, other.fingerprint);
        assert_eq!(
            measured_from(Some(a.clone()), Some("fixture".into()), Some(b)),
            Placement::default()
        );
        assert_eq!(
            measured_from(None, Some("fixture".into()), Some(a.clone())),
            Placement::default()
        );
        let unknown = measured_from(Some(a.clone()), None, Some(a));
        assert_eq!(unknown.allowed_logical_cpus, Some(2));
        assert!(unknown.fingerprint.is_none());
        let huge: BTreeSet<_> = (0..=MAX_CPUS).collect();
        assert_eq!(
            measured_from(Some(huge.clone()), Some("fixture".into()), Some(huge)),
            Placement::default()
        );
    }

    #[test]
    fn complete_domains_canonicalize_and_reject_missing_or_duplicate_cpus() {
        let allowed = BTreeSet::from([0, 1, 2, 3]);
        let mut groups = vec![vec![3, 2], vec![1, 0]];
        assert!(complete_groups(&allowed, &mut groups));
        assert_eq!(groups, vec![vec![0, 1], vec![2, 3]]);
        assert!(!complete_groups(&allowed, &mut [vec![0, 1], vec![1, 2, 3]]));
        assert!(!complete_groups(&allowed, &mut [vec![0, 1], vec![2]]));
        assert!(!complete_domains(
            &allowed,
            &mut [vec![0, 1], vec![2, 3]],
            &mut [vec![0, 1, 2, 3]],
            &mut [vec![0, 2], vec![1, 3]]
        ));
    }

    #[test]
    fn slow_probe_backs_off_with_unknown_instead_of_stale_data() {
        let mut sampler = PlacementSampler::with_probe(|| panic!("must not probe during backoff"));
        let now = Instant::now();
        let known = Placement {
            allowed_logical_cpus: Some(4),
            fingerprint: Some("a".repeat(64)),
        };
        assert_eq!(
            sampler.accept(
                known.clone(),
                now,
                now + SLOW_PROBE + Duration::from_millis(1)
            ),
            Placement::default()
        );
        assert_eq!(sampler.sample(), Placement::default());
        assert_eq!(sampler.accept(known.clone(), now, now), known);
        assert!(sampler.retry_after.is_none());
    }

    #[test]
    #[ignore = "manual metadata-overhead measurement; no hashing or GPU work"]
    fn measure_native_placement_overhead() {
        let mut micros = Vec::new();
        let mut known = 0;
        for _ in 0..20 {
            let now = Instant::now();
            let observation = measure();
            micros.push(now.elapsed().as_micros());
            known += usize::from(observation.fingerprint.is_some());
        }
        micros.sort_unstable();
        println!(
            "placement probe: known={known}/20 p50={}us p95={}us max={}us",
            micros[10], micros[18], micros[19]
        );
    }
}
