//! Spawn and monitor the Python sidecar process. Restart on exit with 2s delay.
//! On app exit we kill the sidecar so the port is released for the next launch.

use std::path::PathBuf;
use std::process::Child;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use tauri::{AppHandle, Emitter, Manager, Runtime};

/// Shared state: current sidecar process ID (when running) and a flag to stop the restart loop.
#[derive(Clone)]
pub struct SidecarState {
    pub pid: Arc<Mutex<Option<u32>>>,
    pub stop: Arc<AtomicBool>,
}

/// Config path for settings.json (e.g. ~/.config/dictate/settings.json).
pub fn config_path<R: Runtime>(app: &AppHandle<R>) -> Option<PathBuf> {
    app.path()
        .app_config_dir()
        .ok()
        .map(|p: PathBuf| p.join("settings.json"))
}

/// In dev: run `python3 sidecar/main.py --config <path>`.
/// In prod: spawn sidecar binary with --config.
pub fn start_sidecar(app: &AppHandle) -> Result<Option<Child>, String> {
    let config_path = config_path(app)
        .ok_or_else(|| "No config dir".to_string())?
        .to_string_lossy()
        .to_string();

    #[cfg(debug_assertions)]
    {
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string());
        let sidecar_dir = PathBuf::from(&manifest_dir).join("..").join("sidecar");
        let sidecar_main = sidecar_dir
            .join("main.py")
            .canonicalize()
            .map_err(|e| format!("sidecar path: {}", e))?;
        let python = which_python(&sidecar_dir);
        let sidecar_cwd = sidecar_dir
            .canonicalize()
            .unwrap_or_else(|_| sidecar_dir.clone());
        let child = std::process::Command::new(python)
            .current_dir(&sidecar_cwd)
            .arg(sidecar_main.to_string_lossy().to_string())
            .arg("--config")
            .arg(&config_path)
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;
        return Ok(Some(child));
    }

    #[cfg(not(debug_assertions))]
    {
        let sidecar = app
            .shell()
            .sidecar("dictate-sidecar")
            .map_err(|e| e.to_string())?
            .args(["--config", &config_path]);
        let (_rx, _child) = sidecar.spawn().map_err(|e| e.to_string())?;
        return Ok(None);
    }
}

/// Prefer sidecar/.venv/bin/python in dev so uvicorn and deps are available.
fn which_python(sidecar_dir: &PathBuf) -> String {
    let venv_python = sidecar_dir.join(".venv").join("bin").join("python");
    if venv_python.exists() {
        return venv_python.to_string_lossy().to_string();
    }
    if std::process::Command::new("python3").arg("--version").output().is_ok() {
        "python3".to_string()
    } else {
        "python".to_string()
    }
}

/// Spawn sidecar and run restart loop in background.
pub fn run_sidecar_loop(app: AppHandle, state: SidecarState) {
    let pid_guard = state.pid.clone();
    std::thread::spawn(move || {
        while !state.stop.as_ref().load(Ordering::SeqCst) {
            match start_sidecar(&app) {
                Ok(Some(mut child)) => {
                    {
                        let pid = child.id();
                        if let Ok(mut guard) = pid_guard.lock() {
                            *guard = Some(pid);
                        }
                    }
                    let _ = child.wait();
                    if let Ok(mut guard) = pid_guard.lock() {
                        *guard = None;
                    }
                }
                Ok(None) => {
                    std::thread::sleep(Duration::from_secs(60));
                }
                Err(e) => {
                    let _ = app.emit("sidecar_error", e);
                }
            }
            if state.stop.as_ref().load(Ordering::SeqCst) {
                break;
            }
            let _ = app.emit("sidecar_exited", ());
            std::thread::sleep(Duration::from_secs(2));
            if state.stop.as_ref().load(Ordering::SeqCst) {
                break;
            }
            let _ = app.emit("sidecar_restarted", ());
        }
    });
}

/// Kill the sidecar process by PID so the port is released when the app quits.
pub fn kill_sidecar_if_running(pid: u32) {
    #[cfg(unix)]
    {
        let _ = std::process::Command::new("kill")
            .arg("-TERM")
            .arg(pid.to_string())
            .output();
    }
    #[cfg(windows)]
    {
        let _ = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/F"])
            .output();
    }
}
