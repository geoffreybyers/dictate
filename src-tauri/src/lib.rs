mod hotkey;
mod sidecar;
mod tray;
mod websocket;

use serde_json::Value;
use std::sync::atomic::Ordering;
use tauri::{Manager, RunEvent};
use tokio::sync::mpsc;

#[tauri::command]
fn get_config_path(app: tauri::AppHandle) -> Option<String> {
    sidecar::config_path(&app).map(|p| p.to_string_lossy().to_string())
}

/// Returns the OS color scheme for "auto" theme so the WebView doesn't rely on matchMedia (which can be wrong in Tauri).
///
/// On Linux we query the XDG Settings portal (`org.freedesktop.appearance`
/// `color-scheme`) directly — the `dark-light` crate's v1 GNOME detection is
/// broken: it looks for "dark" in the gtk-theme name, but modern GNOME uses
/// plain "Adwaita" with a separate `color-scheme` key, so it always returns
/// light even on dark systems.
#[tauri::command]
fn get_system_theme() -> &'static str {
    #[cfg(target_os = "linux")]
    {
        if let Some(t) = linux_color_scheme() {
            return t;
        }
    }
    match dark_light::detect() {
        dark_light::Mode::Dark => "dark",
        dark_light::Mode::Light => "light",
        dark_light::Mode::Default => "dark", // fallback when unknown
    }
}

/// Ask the XDG Settings portal for the system color-scheme. Values:
///   0 = no preference, 1 = prefer dark, 2 = prefer light.
/// Falls back to gsettings org.gnome.desktop.interface color-scheme.
#[cfg(target_os = "linux")]
fn linux_color_scheme() -> Option<&'static str> {
    use zbus::blocking::Connection;

    // Try the XDG portal first — works across GNOME/KDE/etc.
    if let Ok(conn) = Connection::session() {
        let reply = conn.call_method(
            Some("org.freedesktop.portal.Desktop"),
            "/org/freedesktop/portal/desktop",
            Some("org.freedesktop.portal.Settings"),
            "Read",
            &("org.freedesktop.appearance", "color-scheme"),
        );
        if let Ok(msg) = reply {
            // The reply is variant(variant(uint32)). Deserialize as nested.
            if let Ok(inner) = msg.body().deserialize::<zbus::zvariant::Value>() {
                if let Some(v) = unwrap_variant_u32(&inner) {
                    return match v {
                        1 => Some("dark"),
                        2 => Some("light"),
                        _ => None, // 0 = no preference
                    };
                }
            }
        }
    }

    // Fallback: gsettings (GNOME only).
    if let Ok(out) = std::process::Command::new("gsettings")
        .args(["get", "org.gnome.desktop.interface", "color-scheme"])
        .output()
    {
        if out.status.success() {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if s.contains("prefer-dark") {
                return Some("dark");
            }
            if s.contains("prefer-light") || s.contains("default") {
                return Some("light");
            }
        }
    }

    None
}

/// Recursively unwrap nested `zvariant::Value::Value(...)` until we find a U32.
#[cfg(target_os = "linux")]
fn unwrap_variant_u32(v: &zbus::zvariant::Value) -> Option<u32> {
    use zbus::zvariant::Value;
    match v {
        Value::U32(n) => Some(*n),
        Value::Value(inner) => unwrap_variant_u32(inner),
        _ => None,
    }
}

#[tauri::command]
fn start_recording(state: tauri::State<'_, websocket::WsCommandSender>) {
    websocket::send_command(state, "start_recording", None);
}

#[tauri::command]
fn stop_recording(state: tauri::State<'_, websocket::WsCommandSender>) {
    websocket::send_command(state, "stop_recording", None);
}

#[tauri::command]
fn toggle_recording(state: tauri::State<'_, websocket::WsCommandSender>) {
    websocket::send_command(state, "toggle_recording", None);
}

/// Forward a `toggle_recording` message out over the main WebSocket.
/// Used by the single-instance callback (second `dictate --toggle` invocation)
/// and by the cold-start argv check.
pub(crate) fn forward_toggle(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<websocket::WsCommandSender>() {
        let _ = state.0.send(r#"{"type":"toggle_recording"}"#.to_string());
    }
}

#[tauri::command]
fn update_settings(state: tauri::State<'_, websocket::WsCommandSender>, settings: Value) {
    websocket::send_command(state, "update_settings", Some(settings));
}

#[tauri::command]
fn get_status(state: tauri::State<'_, websocket::WsCommandSender>) {
    websocket::send_command(state, "get_status", None);
}

#[tauri::command]
fn register_hotkey_cmd(app: tauri::AppHandle, hotkey: String) -> Result<(), String> {
    hotkey::register_hotkey(&app, &hotkey).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_hotkey_backend() -> &'static str {
    hotkey::current_backend()
}

#[tauri::command]
fn set_tray_status(app: tauri::AppHandle, status: String) {
    tray::update_icon_for_status(&app, &status);
}

/// OS version string for Developer screen (stub: OS name; full version would need platform-specific code).
#[tauri::command]
fn get_os_version() -> String {
    let name = std::env::consts::OS;
    match name {
        "macos" => "macOS".to_string(),
        "windows" => "Windows".to_string(),
        "linux" => "Linux".to_string(),
        other => other.to_string(),
    }
}

/// Input (microphone) devices for Developer screen. Stub: returns empty list; real list would come from sidecar/audio backend.
#[tauri::command]
fn get_input_devices() -> Vec<InputDevice> {
    vec![]
}

#[derive(serde::Serialize)]
struct InputDevice {
    id: String,
    label: String,
}

/// Kill the current sidecar process so run_sidecar_loop will restart it after 2s.
#[tauri::command]
fn restart_sidecar(state: tauri::State<'_, sidecar::SidecarState>) -> Result<(), String> {
    if let Ok(mut guard) = state.pid.lock() {
        if let Some(pid) = *guard {
            sidecar::kill_sidecar_if_running(pid);
            *guard = None;
        }
    }
    Ok(())
}

/// Return saved window bounds from settings.json for frontend to restore.
#[tauri::command]
fn get_saved_window_bounds(app: tauri::AppHandle) -> Option<(u32, u32, Option<i32>, Option<i32>)> {
    let path = sidecar::config_path(&app)?;
    let s = std::fs::read_to_string(&path).ok()?;
    let j: Value = serde_json::from_str(&s).ok()?;
    let w = j.get("window_width")?.as_u64()? as u32;
    let h = j.get("window_height")?.as_u64()? as u32;
    let x = j.get("window_x").and_then(|v| v.as_i64()).map(|v| v as i32);
    let y = j.get("window_y").and_then(|v| v.as_i64()).map(|v| v as i32);
    Some((w, h, x, y))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // single-instance MUST be the first plugin so it short-circuits
        // duplicate launches (e.g. `dictate --toggle` spawned by the GNOME
        // media-keys binding) before we do any other setup.
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            // Second-instance callback runs in the ORIGINAL process.
            // argv is the duplicate invocation's argv. Route --toggle
            // through the existing WebSocket.
            if argv.iter().any(|a| a == "--toggle") {
                forward_toggle(app);
            } else {
                // Bare `dictate` re-launch: surface the settings window.
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_positioner::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let (cmd_tx, cmd_rx) = mpsc::unbounded_channel();
            app.manage(websocket::WsCommandSender(cmd_tx));
            let sidecar_state = sidecar::SidecarState {
                pid: std::sync::Arc::new(std::sync::Mutex::new(None)),
                stop: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
            };
            app.manage(sidecar_state.clone());
            let handle = app.handle().clone();
            sidecar::run_sidecar_loop(handle.clone(), sidecar_state);
            tauri::async_runtime::spawn(async move {
                websocket::run_websocket_loop(handle, cmd_rx).await;
            });
            if let Err(e) = tray::setup_tray(&app.handle()) {
                eprintln!("Tray setup failed: {}", e);
            }
            hotkey::register_hotkey_from_config(&app.handle());
            // Cold start: if we were launched with --toggle (no other instance
            // existed), fire a toggle once the WS loop has a chance to connect.
            // The message is queued in the unbounded channel until the socket is up.
            if std::env::args().any(|a| a == "--toggle") {
                forward_toggle(&app.handle());
            }
            // Show settings panel on first run (no settings.json or first_run: true)
            if let Some(path) = sidecar::config_path(&app.handle()) {
                let first_run = std::fs::read_to_string(&path)
                    .ok()
                    .and_then(|s| serde_json::from_str::<Value>(&s).ok())
                    .and_then(|j| j.get("first_run").and_then(|v| v.as_bool()))
                    .unwrap_or(true);
                if first_run {
                    if let Some(win) = app.get_webview_window("main") {
                        // Don't use TrayCenter here: tray position isn't set until user clicks the tray.
                        let _ = win.show();
                        let _ = win.set_focus();
                    }
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_config_path,
            get_system_theme,
            get_os_version,
            get_input_devices,
            restart_sidecar,
            get_saved_window_bounds,
            start_recording,
            stop_recording,
            toggle_recording,
            update_settings,
            get_status,
            register_hotkey_cmd,
            get_hotkey_backend,
            set_tray_status,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let RunEvent::ExitRequested { .. } = event {
                if let Some(state) = app.try_state::<sidecar::SidecarState>() {
                    state.stop.store(true, Ordering::SeqCst);
                    if let Ok(guard) = state.pid.lock() {
                        if let Some(pid) = *guard {
                            sidecar::kill_sidecar_if_running(pid);
                        }
                    }
                }
            }
        });
}
