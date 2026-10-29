// Append to src/miner/thread_showcase.rs temporarily and run only this ignored test.
// Uses the real dashboard renderer; no hashing, network I/O or wallet is started.
#[test]
#[ignore = "exports an editorial screenshot with explicitly synthetic counters"]
fn export_setup_guide_dashboard() {
    let mut state = TuiStateInner::new();
    state.version = env!("CARGO_PKG_VERSION").into();
    state.mode = "pool".into();
    state.state = "hashing".into();
    state.threads = 2;
    state.pool_worker = "demo-pc".into();
    state.api_url = "stratum+tcp://bntpool.com:3333".into();
    state.backends_desc = "cpu".into();
    state.round_hashrate = "2.500 H/s".into();
    state.avg_hashrate = "2.400 H/s".into();
    state.total_hashes = 240;
    state.submitted = 5;
    state.accepted = 5;
    let html = format!(
        "<!doctype html><html lang='en'><meta charset='utf-8'><title>Seine dashboard — example data</title><style>body{{margin:0;padding:16px;background:#080b10;color:#b4bec8;width:max-content}}pre{{margin:0;height:180px;overflow:hidden;font:16px/1.25 Consolas,monospace}}.label{{font:14px/1.5 system-ui;margin-bottom:8px;color:#b4bec8}}</style><div class='label'>Seine dashboard · example data, not a benchmark</div>{}",
        capture(&state, 100, 30)
    );
    std::fs::write("/tmp/seine-setup-dashboard.html", &html).unwrap();
    let mobile = html.replace(&capture(&state, 100, 30), &capture(&state, 40, 8))
        .replace("height:180px", "height:160px")
        .replace("Seine dashboard · example data, not a benchmark", "Seine · example data");
    std::fs::write("/tmp/seine-setup-dashboard-mobile.html", mobile).unwrap();
}
