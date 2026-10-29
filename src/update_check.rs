//! Background check for newer seine releases.
//!
//! One request to the GitHub releases API at startup and every
//! `CHECK_INTERVAL` after. A newer release is logged once per version and
//! flagged in the dashboard header. Failures are silent; the next interval
//! retries.

use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use anyhow::{bail, Context, Result};
use serde::Deserialize;

use crate::miner::ui;

const LATEST_RELEASE_API_URL: &str = "https://api.github.com/repos/zpalmtree/seine/releases/latest";
const RELEASES_URL: &str = "https://github.com/zpalmtree/seine/releases/latest";
const CHECK_INTERVAL: Duration = Duration::from_secs(12 * 60 * 60);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(10);

static STATE: Mutex<UpdateState> = Mutex::new(UpdateState {
    latest: None,
    tui_log_pending: false,
});

struct UpdateState {
    latest: Option<String>,
    // Set when the notice was announced before any dashboard existed, so the
    // first dashboard built afterwards still shows it in its log.
    tui_log_pending: bool,
}

#[derive(Deserialize)]
struct LatestRelease {
    tag_name: String,
}

pub(crate) struct DashboardUpdate {
    pub latest: String,
    pub log_message: Option<String>,
}

pub(crate) fn spawn(auto_update: bool, shutdown: Arc<AtomicBool>) {
    let current = crate::version::release_version();
    // Untagged development builds have nothing meaningful to compare.
    if parse_version(current).is_none() {
        return;
    }
    let _ = thread::Builder::new()
        .name("update-check".to_string())
        .spawn(move || loop {
            if let Ok(tag) = fetch_latest_tag() {
                record_latest(current, &tag);
                if auto_update && is_newer(&tag, current) && apply_update(&shutdown) {
                    return;
                }
            }
            thread::sleep(CHECK_INTERVAL);
        });
}

/// `--auto-update`: install the newer release, then stop mining so `main` can
/// restart the updated executable with the same arguments. A failed attempt is
/// retried at the next check.
fn apply_update(shutdown: &Arc<AtomicBool>) -> bool {
    match crate::self_update::run() {
        Ok(crate::self_update::Outcome::Updated { from, to, .. }) => {
            ui::info(
                "UPDATE",
                format!("installed seine {to} (was {from}); restarting with the same arguments"),
            );
            crate::self_update::request_restart();
            crate::shutdown::request_auto_update(shutdown);
            true
        }
        Ok(crate::self_update::Outcome::UpToDate { .. }) => false,
        Err(err) => {
            ui::warn(
                "UPDATE",
                format!("automatic update failed: {err:#}; retrying at the next check"),
            );
            false
        }
    }
}

/// The newer release for a dashboard being built, plus its log line if it was
/// announced before any dashboard could show it.
pub(crate) fn for_new_dashboard() -> Option<DashboardUpdate> {
    let mut state = STATE.lock().unwrap_or_else(|e| e.into_inner());
    let latest = state.latest.clone()?;
    let log_message = std::mem::take(&mut state.tui_log_pending).then(|| notice(&latest));
    Some(DashboardUpdate {
        latest,
        log_message,
    })
}

fn record_latest(current: &str, tag: &str) {
    if !is_newer(tag, current) {
        return;
    }
    let already_announced = STATE
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .latest
        .as_deref()
        == Some(tag);
    if already_announced {
        return;
    }
    // Announce without holding STATE: the dashboard builder takes STATE while
    // the announcement takes the dashboard lock.
    let delivered_to_tui = ui::announce_update(tag, &notice(tag));
    let mut state = STATE.lock().unwrap_or_else(|e| e.into_inner());
    state.latest = Some(tag.to_string());
    state.tui_log_pending = !delivered_to_tui;
}

fn notice(latest: &str) -> String {
    format!(
        "seine {latest} is available (running {}): {RELEASES_URL}",
        crate::version::ui_display_version()
    )
}

fn fetch_latest_tag() -> Result<String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(REQUEST_TIMEOUT)
        .user_agent(format!("seine/{}", crate::version::release_version()))
        .build()?;
    let response = client
        .get(LATEST_RELEASE_API_URL)
        .header("Accept", "application/vnd.github+json")
        .send()
        .context("release check unavailable")?;
    if !response.status().is_success() {
        bail!("release check returned {}", response.status());
    }
    let release: LatestRelease = response.json().context("invalid release response")?;
    Ok(release.tag_name)
}

pub(crate) fn is_newer(candidate: &str, current: &str) -> bool {
    match (parse_version(candidate), parse_version(current)) {
        (Some(candidate), Some(current)) => candidate > current,
        _ => false,
    }
}

/// Parses `v1.2.3` / `1.2.3`, ignoring any `-pre` or `+build` suffix
/// (including `git describe` output such as `v0.2.22-3-gabc1234`).
fn parse_version(raw: &str) -> Option<(u64, u64, u64)> {
    let trimmed = raw.trim();
    let trimmed = trimmed
        .strip_prefix('v')
        .or_else(|| trimmed.strip_prefix('V'))
        .unwrap_or(trimmed);
    let core = trimmed.split(['-', '+']).next()?;
    let mut parts = core.split('.');
    let major = parts.next()?.parse().ok()?;
    let minor = parts.next()?.parse().ok()?;
    let patch = parts.next()?.parse().ok()?;
    if parts.next().is_some() {
        return None;
    }
    Some((major, minor, patch))
}

#[cfg(test)]
mod tests {
    use super::{is_newer, parse_version};

    #[test]
    fn parses_release_tags_and_describe_output() {
        assert_eq!(parse_version("v0.2.22"), Some((0, 2, 22)));
        assert_eq!(parse_version("0.2.22"), Some((0, 2, 22)));
        assert_eq!(parse_version("v0.2.22-3-gabc1234"), Some((0, 2, 22)));
        assert_eq!(parse_version("v1.0.0+build.7"), Some((1, 0, 0)));
    }

    #[test]
    fn rejects_non_version_strings() {
        assert_eq!(parse_version("abc1234"), None);
        assert_eq!(parse_version("v0.2"), None);
        assert_eq!(parse_version("v0.2.22.1"), None);
        assert_eq!(parse_version(""), None);
    }

    #[test]
    fn newer_compares_numerically() {
        assert!(is_newer("v0.2.23", "v0.2.22"));
        assert!(is_newer("v0.10.0", "v0.9.9"));
        assert!(is_newer("v1.0.0", "0.2.22"));
        assert!(!is_newer("v0.2.22", "v0.2.22"));
        assert!(!is_newer("v0.2.21", "v0.2.22"));
        assert!(!is_newer("v0.2.22", "v0.2.22-3-gabc1234"));
        assert!(!is_newer("garbage", "v0.2.22"));
    }
}
