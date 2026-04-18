//! Global hotkey registration.
//!
//! Three backends:
//!   * `legacy`        – `tauri-plugin-global-shortcut` (macOS, Windows, Linux/X11).
//!   * `portal`        – `org.freedesktop.portal.GlobalShortcuts` via `ashpd`
//!                       (KDE Plasma 6+, Sway w/ xdg-desktop-portal-wlr,
//!                       sandboxed/Flatpak GNOME).
//!   * `gnome_fallback`– GNOME custom keybinding via `gsettings` + a
//!                       `dictate --toggle` CLI (unsandboxed GNOME, where
//!                       the portal isn't exposed to host apps).
//!
//! On Linux Wayland we probe the portal at runtime; if it's missing we
//! fall back to `gnome_fallback` when the desktop is GNOME, otherwise
//! return a clear error.

use crate::sidecar;
use crate::websocket::WsCommandSender;
use tauri::{AppHandle, Manager, Runtime};

#[cfg(target_os = "linux")]
mod gnome_fallback;
#[cfg(target_os = "linux")]
mod portal;

/// Register the given hotkey. Empty string unregisters.
pub fn register_hotkey<R: Runtime>(
    app: &AppHandle<R>,
    hotkey: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let hotkey = hotkey.trim();

    #[cfg(target_os = "linux")]
    {
        if is_wayland() {
            if portal_available() {
                return portal::register(app, hotkey);
            }
            if is_gnome() {
                return gnome_fallback::register(app, hotkey);
            }
            return Err("No global shortcut backend available: this compositor doesn't expose the XDG GlobalShortcuts portal and isn't GNOME. Consider using Flatpak or binding the hotkey manually.".into());
        }
    }

    register_legacy(app, hotkey)
}

/// Read hotkey from config and register. Called at startup.
pub fn register_hotkey_from_config<R: Runtime>(app: &AppHandle<R>) {
    let hotkey: String = sidecar::config_path(app)
        .and_then(|p| std::fs::read_to_string(&p).ok())
        .and_then(|s: String| serde_json::from_str::<serde_json::Value>(&s).ok())
        .and_then(|v: serde_json::Value| {
            v.get("hotkey").and_then(|v| v.as_str()).map(String::from)
        })
        .unwrap_or_else(|| "Space".to_string());
    if let Err(e) = register_hotkey(app, &hotkey) {
        eprintln!("Hotkey registration failed: {}", e);
    }
}

/// Returns true on Linux Wayland sessions. False on X11 and non-Linux.
#[cfg(target_os = "linux")]
pub fn is_wayland() -> bool {
    std::env::var("XDG_SESSION_TYPE")
        .map(|v| v.eq_ignore_ascii_case("wayland"))
        .unwrap_or(false)
        || std::env::var("WAYLAND_DISPLAY").is_ok()
}

#[cfg(not(target_os = "linux"))]
pub fn is_wayland() -> bool {
    false
}

#[cfg(target_os = "linux")]
fn is_gnome() -> bool {
    std::env::var("XDG_CURRENT_DESKTOP")
        .map(|v| v.to_ascii_lowercase().contains("gnome"))
        .unwrap_or(false)
}

/// Probe whether the XDG GlobalShortcuts portal is reachable.
/// Cached after the first call.
#[cfg(target_os = "linux")]
fn portal_available() -> bool {
    use std::sync::OnceLock;
    static CACHED: OnceLock<bool> = OnceLock::new();
    if let Some(v) = CACHED.get() {
        return *v;
    }
    let result = probe_portal();
    let _ = CACHED.set(result);
    result
}

#[cfg(target_os = "linux")]
fn probe_portal() -> bool {
    // Use a one-shot blocking zbus call to introspect the portal object
    // and look for the GlobalShortcuts interface. Avoids spinning up an
    // ashpd session just to probe.
    use zbus::blocking::Connection;

    let conn = match Connection::session() {
        Ok(c) => c,
        Err(_) => return false,
    };
    let body: Result<String, _> = conn
        .call_method(
            Some("org.freedesktop.portal.Desktop"),
            "/org/freedesktop/portal/desktop",
            Some("org.freedesktop.DBus.Introspectable"),
            "Introspect",
            &(),
        )
        .and_then(|m| m.body().deserialize::<String>());
    match body {
        Ok(xml) => xml.contains("org.freedesktop.portal.GlobalShortcuts"),
        Err(_) => false,
    }
}

/// Returns the active hotkey backend identifier for the frontend.
pub fn current_backend() -> &'static str {
    #[cfg(target_os = "linux")]
    {
        if is_wayland() {
            if portal_available() {
                return "portal";
            }
            if is_gnome() {
                return "gnome-fallback";
            }
            return "unavailable";
        }
    }
    "legacy"
}

// ---------------------------------------------------------------------------
// Legacy backend (tauri-plugin-global-shortcut)
// ---------------------------------------------------------------------------

fn register_legacy<R: Runtime>(
    app: &AppHandle<R>,
    hotkey: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use tauri_plugin_global_shortcut::{ShortcutEvent, ShortcutState};

    let gs = app
        .try_state::<tauri_plugin_global_shortcut::GlobalShortcut<R>>()
        .ok_or("GlobalShortcut not available")?;
    let _ = gs.unregister_all();
    if hotkey.is_empty() {
        return Ok(());
    }
    let cmd_tx = app
        .try_state::<WsCommandSender>()
        .ok_or("WsCommandSender not available")?;
    let cmd_tx = cmd_tx.0.clone();
    gs.on_shortcut(hotkey, move |_app, _shortcut, event: ShortcutEvent| {
        let msg = match event.state {
            ShortcutState::Pressed => r#"{"type":"start_recording"}"#,
            ShortcutState::Released => r#"{"type":"stop_recording"}"#,
        };
        let _ = cmd_tx.send(msg.to_string());
    })?;
    Ok(())
}
