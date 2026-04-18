//! GNOME fallback backend.
//!
//! Used on Wayland sessions where the XDG GlobalShortcuts portal is NOT
//! exposed to unsandboxed apps (default GNOME policy). We register a
//! GNOME custom keyboard shortcut via `gsettings` whose `command` invokes
//! `dictate --toggle`. That CLI shoots a single `toggle_recording`
//! message at the sidecar's WebSocket, so press => start/stop.
//!
//! Limitations:
//!   * GNOME custom keybindings only fire on key PRESS — this is a toggle,
//!     not push-to-talk.
//!   * Requires the `gsettings` binary in PATH.
//!   * The binding shows up in GNOME Settings → Keyboard → Custom Shortcuts.
//!   * Won't work inside sandboxed containers that can't talk to the host
//!     GSettings backend.

use std::error::Error;
use std::process::Command;

use tauri::{AppHandle, Runtime};

const SCHEMA_LIST: &str = "org.gnome.settings-daemon.plugins.media-keys";
const SCHEMA_BIND: &str = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding";
const KEY_LIST: &str = "custom-keybindings";
const PATH: &str = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/dictate/";
const NAME: &str = "Dictate toggle";

pub fn register<R: Runtime>(
    _app: &AppHandle<R>,
    hotkey: &str,
) -> Result<(), Box<dyn Error + Send + Sync>> {
    if hotkey.is_empty() {
        return remove_binding();
    }

    let exe = std::env::current_exe()?;
    let exe_str = exe.to_string_lossy().to_string();
    let command = format!("{} --toggle", shell_quote(&exe_str));
    let accel = to_gnome_accel(hotkey);

    // Ensure our path is in the custom-keybindings list (preserve others).
    let current = gsettings_get(SCHEMA_LIST, KEY_LIST)?;
    let mut paths = parse_string_array(&current);
    if !paths.iter().any(|p| p == PATH) {
        paths.push(PATH.to_string());
    }
    gsettings_set(SCHEMA_LIST, KEY_LIST, &format_string_array(&paths))?;

    // Set the binding's name, command, and binding accelerator.
    gsettings_set_path(SCHEMA_BIND, PATH, "name", &gvariant_string(NAME))?;
    gsettings_set_path(SCHEMA_BIND, PATH, "command", &gvariant_string(&command))?;
    gsettings_set_path(SCHEMA_BIND, PATH, "binding", &gvariant_string(&accel))?;

    Ok(())
}

fn remove_binding() -> Result<(), Box<dyn Error + Send + Sync>> {
    // Try to update the list, ignoring failures (gsettings may not exist
    // on this system).
    if let Ok(current) = gsettings_get(SCHEMA_LIST, KEY_LIST) {
        let paths: Vec<String> = parse_string_array(&current)
            .into_iter()
            .filter(|p| p != PATH)
            .collect();
        let new_val = if paths.is_empty() {
            "@as []".to_string()
        } else {
            format_string_array(&paths)
        };
        gsettings_set(SCHEMA_LIST, KEY_LIST, &new_val)?;
    }
    Ok(())
}

fn gsettings_get(schema: &str, key: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
    let out = Command::new("gsettings").args(["get", schema, key]).output()?;
    if !out.status.success() {
        return Err(format!(
            "gsettings get {schema} {key} failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        )
        .into());
    }
    Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

fn gsettings_set(schema: &str, key: &str, value: &str) -> Result<(), Box<dyn Error + Send + Sync>> {
    let out = Command::new("gsettings")
        .args(["set", schema, key, value])
        .output()?;
    if !out.status.success() {
        return Err(format!(
            "gsettings set {schema} {key} failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        )
        .into());
    }
    Ok(())
}

fn gsettings_set_path(
    schema: &str,
    path: &str,
    key: &str,
    value: &str,
) -> Result<(), Box<dyn Error + Send + Sync>> {
    let target = format!("{schema}:{path}");
    let out = Command::new("gsettings")
        .args(["set", &target, key, value])
        .output()?;
    if !out.status.success() {
        return Err(format!(
            "gsettings set {target} {key} failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        )
        .into());
    }
    Ok(())
}

/// Parse a GVariant 'as' (array of strings), e.g. `['a', 'b']` or `@as []`.
fn parse_string_array(s: &str) -> Vec<String> {
    let s = s.trim();
    if s.is_empty() || s == "@as []" || s == "[]" {
        return Vec::new();
    }
    let inner = s.trim_start_matches("@as ").trim();
    let inner = inner.trim_start_matches('[').trim_end_matches(']');
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut in_str = false;
    let mut quote: char = '\'';
    for c in inner.chars() {
        if in_str {
            if c == quote {
                out.push(cur.clone());
                cur.clear();
                in_str = false;
            } else {
                cur.push(c);
            }
        } else if c == '\'' || c == '"' {
            in_str = true;
            quote = c;
        }
    }
    out
}

fn format_string_array(paths: &[String]) -> String {
    let parts: Vec<String> = paths.iter().map(|p| gvariant_string(p)).collect();
    format!("[{}]", parts.join(", "))
}

fn gvariant_string(s: &str) -> String {
    // Escape backslashes and single quotes for GVariant 's' literal.
    let escaped = s.replace('\\', "\\\\").replace('\'', "\\'");
    format!("'{}'", escaped)
}

fn shell_quote(s: &str) -> String {
    // GNOME's media-keys runs `command` through a shell; quote the path
    // safely. Single-quote and escape embedded single quotes.
    let escaped = s.replace('\'', "'\\''");
    format!("'{}'", escaped)
}

/// Translate internal hotkey notation (Tauri accelerator-ish) into the
/// GTK accelerator format gsettings expects, e.g.:
///   "Ctrl+R"        -> "<Primary>r"
///   "Super+Space"   -> "<Super>space"
///   "F9"            -> "F9"
///   "Space"         -> "space"
pub fn to_gnome_accel(s: &str) -> String {
    let mut mods = String::new();
    let mut key = String::new();
    for raw in s.split('+') {
        let p = raw.trim();
        if p.is_empty() {
            continue;
        }
        match p.to_ascii_lowercase().as_str() {
            "ctrl" | "control" | "cmd" | "command" | "cmdorctrl" => mods.push_str("<Primary>"),
            "alt" | "option" => mods.push_str("<Alt>"),
            "shift" => mods.push_str("<Shift>"),
            "super" | "meta" | "win" => mods.push_str("<Super>"),
            other => {
                // F-keys uppercase, everything else lowercase.
                let is_fkey = other.starts_with('f')
                    && other.len() > 1
                    && other[1..].chars().all(|c| c.is_ascii_digit());
                key = if is_fkey {
                    p.to_ascii_uppercase()
                } else {
                    p.to_ascii_lowercase()
                };
            }
        }
    }
    format!("{mods}{key}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accel_basic() {
        assert_eq!(to_gnome_accel("Ctrl+R"), "<Primary>r");
        assert_eq!(to_gnome_accel("Super+Space"), "<Super>space");
        assert_eq!(to_gnome_accel("Space"), "space");
        assert_eq!(to_gnome_accel("F9"), "F9");
        assert_eq!(to_gnome_accel("Ctrl+Shift+D"), "<Primary><Shift>d");
    }

    #[test]
    fn parse_array() {
        assert_eq!(parse_string_array("@as []"), Vec::<String>::new());
        assert_eq!(
            parse_string_array("['/a/', '/b/']"),
            vec!["/a/".to_string(), "/b/".to_string()]
        );
    }
}
