mod address;
mod backend;
mod config;
mod console_exit;
mod control_api;
mod daemon_api;
mod dev_fee;
mod diagnostics;
mod hardware_telemetry;
mod miner;
mod pool;
mod runtime_identity;
mod shortname;
mod shutdown;
mod types;
mod update_check;
mod user_config;
mod version;

use std::sync::atomic::AtomicBool;
use std::sync::Arc;

use anyhow::Result;

use config::Config;

fn main() {
    if let Err(err) = run() {
        eprintln!("fatal: {err:#}");
        console_exit::pause_after_error();
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let cfg = Config::parse()?;
    if cfg.update_check_enabled && !cfg.bench {
        update_check::spawn();
    }

    let shutdown = Arc::new(AtomicBool::new(false));
    let _shutdown_guard = shutdown::install(Arc::clone(&shutdown))?;

    if cfg.api_server_enabled || cfg.service_mode {
        return control_api::run(cfg, shutdown);
    }

    if !cfg.bench && miner::should_enable_tui(&cfg) {
        return control_api::run_interactive(cfg, shutdown);
    }

    miner::run(&cfg, shutdown)
}
