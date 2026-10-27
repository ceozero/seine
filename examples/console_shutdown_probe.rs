//! Native Windows regression probe. Creates and closes only its own hidden console.
//! Run with `<output-directory> <fixed|legacy|stuck|interrupt|forced-interrupt>`.
//! Never starts mining.
#[cfg(target_os = "windows")]
#[path = "../src/shutdown.rs"]
mod shutdown;

#[cfg(target_os = "windows")]
fn main() -> anyhow::Result<()> {
    use std::{
        path::PathBuf,
        sync::{
            atomic::{AtomicBool, Ordering},
            Arc,
        },
        time::Duration,
    };
    use windows_sys::Win32::System::Console::{
        AllocConsole, FreeConsole, GenerateConsoleCtrlEvent, GetConsoleWindow, CTRL_BREAK_EVENT,
    };
    #[link(name = "user32")]
    extern "system" {
        fn PostMessageW(
            window: *mut core::ffi::c_void,
            message: u32,
            wparam: usize,
            lparam: isize,
        ) -> i32;
        fn ShowWindow(window: *mut core::ffi::c_void, command: i32) -> i32;
    }
    let args: Vec<_> = std::env::args_os().collect();
    anyhow::ensure!(
        args.len() == 3,
        "usage: console_shutdown_probe <directory> <fixed|legacy|stuck>"
    );
    let dir = PathBuf::from(&args[1]);
    let mode = args[2].to_str().unwrap_or("");
    anyhow::ensure!(
        ["fixed", "legacy", "stuck", "interrupt", "forced-interrupt"].contains(&mode),
        "invalid mode"
    );
    std::fs::create_dir_all(&dir)?;
    // Detach this disposable process from its launcher; never signal that console.
    unsafe {
        FreeConsole();
    }
    anyhow::ensure!(unsafe { AllocConsole() } != 0, "AllocConsole failed");
    let window = unsafe { GetConsoleWindow() };
    anyhow::ensure!(!window.is_null(), "no owned console window");
    unsafe {
        ShowWindow(window, 0);
    }
    let stop = Arc::new(AtomicBool::new(false));
    let guard = if mode == "legacy" {
        let stop = stop.clone();
        ctrlc::set_handler(move || {
            stop.store(true, Ordering::SeqCst);
        })?;
        None
    } else {
        Some(shutdown::install(stop.clone())?)
    };
    std::fs::write(dir.join("running"), b"unfinished")?;
    let owned_window = window as usize;
    let interrupt = mode.ends_with("interrupt");
    let force = mode == "forced-interrupt";
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(100));
        if interrupt {
            assert_ne!(unsafe { GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, 0) }, 0);
            if force {
                std::thread::sleep(Duration::from_millis(100));
                assert_ne!(unsafe { GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, 0) }, 0);
            }
        } else {
            assert_ne!(unsafe { PostMessageW(owned_window as _, 0x0010, 0, 0) }, 0);
        }
    });
    while !stop.load(Ordering::Acquire) {
        std::thread::sleep(Duration::from_millis(10));
    }
    std::fs::write(
        dir.join("request.json"),
        serde_json::to_vec(&shutdown::requested())?,
    )?;
    std::thread::sleep(Duration::from_millis(if mode == "stuck" || force {
        10_000
    } else {
        250
    }));
    std::fs::remove_file(dir.join("running"))?;
    std::fs::write(dir.join("completed"), b"cleanup finished")?;
    drop(guard);
    Ok(())
}

#[cfg(not(target_os = "windows"))]
fn main() {
    eprintln!("This regression probe requires native Windows.");
    std::process::exit(2);
}
