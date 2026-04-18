//! WebSocket client to sidecar; forward events to frontend; write clipboard on transcription_complete.
//! If auto_paste is enabled, simulate Paste (Ctrl+V / Cmd+V) after writing to clipboard.
//!
//! Paste simulation backends:
//!   * macOS / Windows / Linux X11: `rdev` (works via native APIs / X11).
//!   * Linux Wayland: `ydotool` CLI talking to a user ydotoold daemon
//!     (kernel-level /dev/uinput injection). `rdev` doesn't work on Wayland
//!     and GNOME doesn't expose the virtual-keyboard Wayland protocol to
//!     apps, so ydotool is the only reliable path.

use crate::sidecar;
use futures_util::{SinkExt, StreamExt};
use rdev::{simulate, EventType, Key};
use serde::Deserialize;
use serde_json::Value;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use tauri::{AppHandle, Emitter, State};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream};

const WS_URL: &str = "ws://127.0.0.1:39821/ws";
const CONNECT_RETRY_MS: u64 = 500;
const MAX_RETRIES: u32 = 60;

static RUNNING: AtomicBool = AtomicBool::new(true);

/// Reserved for graceful shutdown (stop retry loop when app exits).
#[allow(dead_code)]
pub fn set_running(r: bool) {
    RUNNING.store(r, Ordering::SeqCst);
}

pub struct WsCommandSender(pub mpsc::UnboundedSender<String>);

#[derive(Debug, Deserialize)]
struct WsMessage {
    #[serde(rename = "type")]
    pub msg_type: String,
    #[serde(default)]
    pub text: Option<String>,
    /// Forwarded to frontend via raw JSON emit; not read here.
    #[serde(default, rename = "code")]
    pub _code: Option<String>,
    #[serde(default, rename = "message")]
    pub _message: Option<String>,
}

/// Connect to sidecar WebSocket and run message loop.
pub async fn run_websocket_loop(app: AppHandle, mut cmd_rx: mpsc::UnboundedReceiver<String>) {
    let mut retries = 0u32;
    while RUNNING.load(Ordering::SeqCst) && retries < MAX_RETRIES {
        match connect_async(WS_URL).await {
            Ok((ws, _)) => {
                retries = 0;
                let (res, rx_opt) = handle_connection(app.clone(), ws, cmd_rx).await;
                cmd_rx = match rx_opt {
                    Some(rx) => rx,
                    None => break,
                };
                if let Err(e) = res {
                    let _ = app.emit("sidecar_event", serde_json::json!({ "type": "error", "code": "WS_ERROR", "message": e.to_string() }));
                }
            }
            Err(_) => {
                retries += 1;
                tokio::time::sleep(Duration::from_millis(CONNECT_RETRY_MS)).await;
            }
        }
    }
    if retries >= MAX_RETRIES {
        let _ = app.emit(
            "sidecar_event",
            serde_json::json!({ "type": "error", "code": "SIDECAR_TIMEOUT", "message": "Sidecar did not connect in time" }),
        );
    }
}

async fn handle_connection(
    app: AppHandle,
    ws: WebSocketStream<MaybeTlsStream<TcpStream>>,
    mut cmd_rx: mpsc::UnboundedReceiver<String>,
) -> (
    Result<(), Box<dyn std::error::Error + Send + Sync>>,
    Option<mpsc::UnboundedReceiver<String>>,
) {
    let (mut write, mut read) = ws.split();
    loop {
        tokio::select! {
            msg = read.next() => {
                match msg {
                    Some(Ok(Message::Text(t))) => {
                        if let Ok(parsed) = serde_json::from_str::<WsMessage>(&t) {
                            if parsed.msg_type == "transcription_complete" {
                                if let Some(ref text) = parsed.text {
                                    let _ = app.clipboard().write_text(text.clone());
                                    if auto_paste_enabled(&app) {
                                        let shortcut = paste_shortcut(&app);
                                        tokio::time::sleep(Duration::from_millis(80)).await;
                                        simulate_paste(&shortcut);
                                    }
                                }
                            }
                        }
                        if let Ok(v) = serde_json::from_str::<Value>(&t) {
                            let _ = app.emit("sidecar_event", v);
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => return (Ok(()), Some(cmd_rx)),
                    Some(Err(e)) => return (Err(e.into()), Some(cmd_rx)),
                    _ => {}
                }
            }
            cmd = cmd_rx.recv() => {
                match cmd {
                    Some(s) => {
                        if let Err(e) = write.send(Message::Text(s)).await {
                            return (Err(e.into()), Some(cmd_rx));
                        }
                    }
                    None => return (Ok(()), None),
                }
            }
        }
    }
}

/// Read auto_paste from settings.json (same path as sidecar config).
fn auto_paste_enabled(app: &AppHandle) -> bool {
    let path = match sidecar::config_path(app) {
        Some(p) => p,
        None => return false,
    };
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return false,
    };
    let data: Value = match serde_json::from_str(&contents) {
        Ok(v) => v,
        Err(_) => return false,
    };
    data.get("auto_paste").and_then(Value::as_bool).unwrap_or(false)
}

/// Read paste_shortcut from settings.json. Returns "ctrl+v" or "ctrl+shift+v".
fn paste_shortcut(app: &AppHandle) -> String {
    let path = match sidecar::config_path(app) {
        Some(p) => p,
        None => return "ctrl+v".to_string(),
    };
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return "ctrl+v".to_string(),
    };
    let data: Value = match serde_json::from_str(&contents) {
        Ok(v) => v,
        Err(_) => return "ctrl+v".to_string(),
    };
    data.get("paste_shortcut")
        .and_then(Value::as_str)
        .unwrap_or("ctrl+v")
        .to_string()
}

/// Simulate Paste: on Linux Wayland delegate to `ydotool`; elsewhere use rdev
/// (Cmd+V on macOS, Ctrl+V or Ctrl+Shift+V on Windows/Linux X11).
fn simulate_paste(shortcut: &str) {
    #[cfg(target_os = "linux")]
    {
        if crate::hotkey::is_wayland() {
            simulate_paste_wayland(shortcut);
            return;
        }
    }
    simulate_paste_rdev(shortcut);
}

/// Wayland paste via `ydotool` (requires running ydotoold user service).
/// Uses ydotool's symbolic key-sequence syntax (`ctrl+shift+v`). The Ubuntu
/// 0.1.x CLI and the modern 1.x CLI both accept this form — the older
/// scancode form (`29:1 47:1 ...`) is not portable: 0.1.8 treats any
/// unrecognized token as literal text to type, which silently corrupts the
/// paste.
#[cfg(target_os = "linux")]
fn simulate_paste_wayland(shortcut: &str) {
    use std::process::Command;
    let combo = if shortcut == "ctrl+shift+v" {
        "ctrl+shift+v"
    } else {
        "ctrl+v"
    };

    // ydotool reads YDOTOOL_SOCKET from env. Socket location depends on how
    // ydotoold was started — common defaults:
    //   * $XDG_RUNTIME_DIR/.ydotool_socket (modern user unit)
    //   * /tmp/.ydotool_socket             (upstream default, Ubuntu 0.1.8)
    // We pick the first one that actually exists. If neither does, leave the
    // env unset and let ydotool error out with its own message.
    let candidates: Vec<String> = [
        std::env::var("YDOTOOL_SOCKET").ok(),
        std::env::var("XDG_RUNTIME_DIR")
            .ok()
            .map(|d| format!("{d}/.ydotool_socket")),
        Some("/tmp/.ydotool_socket".to_string()),
    ]
    .into_iter()
    .flatten()
    .collect();
    let socket = candidates
        .iter()
        .find(|p| std::path::Path::new(p).exists())
        .cloned();

    let mut cmd = Command::new("ydotool");
    cmd.arg("key").arg(combo);
    if let Some(ref s) = socket {
        cmd.env("YDOTOOL_SOCKET", s);
    }
    let result = cmd.output();
    match result {
        Ok(out) if out.status.success() => {}
        Ok(out) => {
            eprintln!(
                "[auto-paste] ydotool failed (exit {:?}): {}",
                out.status.code(),
                String::from_utf8_lossy(&out.stderr).trim()
            );
        }
        Err(e) => {
            eprintln!("[auto-paste] ydotool not available: {e}. Install ydotool + ydotoold and enable the user service. See README.");
        }
    }
}

fn simulate_paste_rdev(shortcut: &str) {
    let delay = Duration::from_millis(20);
    let modifier = if cfg!(target_os = "macos") {
        Key::MetaLeft
    } else {
        Key::ControlLeft
    };
    let use_shift = shortcut == "ctrl+shift+v";
    let send = |event_type: EventType| {
        if simulate(&event_type).is_err() {
            // X11 permission issue or unsupported backend; ignore.
        }
        std::thread::sleep(delay);
    };
    send(EventType::KeyPress(modifier));
    if use_shift {
        send(EventType::KeyPress(Key::ShiftLeft));
    }
    send(EventType::KeyPress(Key::KeyV));
    send(EventType::KeyRelease(Key::KeyV));
    if use_shift {
        send(EventType::KeyRelease(Key::ShiftLeft));
    }
    send(EventType::KeyRelease(modifier));
}

/// Send a JSON command to the sidecar.
pub fn send_command(state: State<'_, WsCommandSender>, cmd: &str, payload: Option<Value>) {
    let s = if cmd == "update_settings" {
        serde_json::json!({ "type": cmd, "settings": payload.unwrap_or(Value::Null) }).to_string()
    } else {
        serde_json::json!({ "type": cmd }).to_string()
    };
    let _ = state.0.send(s);
}
