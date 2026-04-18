// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// `dictate --toggle` is spawned by the GNOME gsettings fallback on every
// hotkey press. We rely on tauri-plugin-single-instance to route argv to
// the already-running instance; the plugin causes this second process to
// exit promptly after delivering. Cold-start (no existing instance) is
// handled in lib.rs by inspecting std::env::args() during setup().
fn main() {
    dictate_lib::run()
}
