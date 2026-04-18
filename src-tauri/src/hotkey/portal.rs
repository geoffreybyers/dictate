//! Wayland backend: XDG GlobalShortcuts portal via `ashpd`.
//!
//! Architecture:
//!   * One long-lived Tokio task owns the portal session.
//!   * It listens for `Activated` / `Deactivated` signals and forwards
//!     them to the existing WebSocket command channel as the same
//!     `start_recording` / `stop_recording` JSON messages the legacy
//!     backend emits — so the rest of the app doesn't care which
//!     backend is in use.
//!   * `register()` sends a message to that task asking it to rebind
//!     the shortcut with a new preferred trigger. The first call spins
//!     the task up; subsequent calls reuse the same session.
//!
//! Portal semantics to be aware of:
//!   * The compositor — not the app — is the source of truth for the
//!     actual key binding. We pass `preferred_trigger`; the user may
//!     override it in the portal's UI.
//!   * `Deactivated` only fires on portal v2 compositors (GNOME 45+,
//!     KDE Plasma 6+). On older ones you get press-only; the app then
//!     behaves like a toggle rather than push-to-talk.
//!   * Sessions do not persist across app restarts; we recreate the
//!     session every launch.

use crate::websocket::WsCommandSender;
use ashpd::desktop::global_shortcuts::{GlobalShortcuts, NewShortcut};
use futures_util::StreamExt;
use std::sync::OnceLock;
use tauri::{AppHandle, Manager, Runtime};
use tokio::sync::mpsc;

/// Identifier we use with the portal. Stable across rebinds.
const SHORTCUT_ID: &str = "dictate.toggle";

/// Human-readable description the portal UI shows the user.
const SHORTCUT_DESCRIPTION: &str = "Push-to-talk dictation";

/// Messages to the portal worker task.
enum Msg {
    /// Bind (or rebind) the shortcut with an optional preferred trigger.
    /// Empty string = unbind (portal has no explicit unbind; we bind
    /// with a sentinel id no keys will match — see worker).
    Bind { preferred: Option<String> },
}

/// Sender handle stashed in Tauri state so `register()` can talk to the worker.
#[derive(Clone)]
struct PortalSender(mpsc::UnboundedSender<Msg>);

/// We only ever spawn one worker per process. Guarded by this flag so
/// repeated `register()` calls don't stack up multiple tasks.
static WORKER_SPAWNED: OnceLock<()> = OnceLock::new();

/// Called from `hotkey::register_hotkey()` on Wayland.
pub fn register<R: Runtime>(
    app: &AppHandle<R>,
    hotkey: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let sender = ensure_worker(app)?;
    let preferred = if hotkey.is_empty() {
        None
    } else {
        Some(normalize_trigger(hotkey))
    };
    sender
        .0
        .send(Msg::Bind { preferred })
        .map_err(|_| "portal worker channel closed")?;
    Ok(())
}

/// Spawn the worker task if not already running. Returns a sender to it.
fn ensure_worker<R: Runtime>(
    app: &AppHandle<R>,
) -> Result<PortalSender, Box<dyn std::error::Error + Send + Sync>> {
    if let Some(sender) = app.try_state::<PortalSender>() {
        return Ok((*sender).clone());
    }

    let cmd_tx = app
        .try_state::<WsCommandSender>()
        .ok_or("WsCommandSender not available")?
        .0
        .clone();

    let (tx, rx) = mpsc::unbounded_channel::<Msg>();
    let sender = PortalSender(tx);
    app.manage(sender.clone());

    if WORKER_SPAWNED.set(()).is_ok() {
        tauri::async_runtime::spawn(async move {
            if let Err(e) = worker(rx, cmd_tx).await {
                eprintln!("[hotkey/portal] worker exited with error: {e:#}");
            }
        });
    }

    Ok(sender)
}

/// Main portal worker loop. Owns the session and signal streams.
async fn worker(
    mut rx: mpsc::UnboundedReceiver<Msg>,
    cmd_tx: tokio::sync::mpsc::UnboundedSender<String>,
) -> ashpd::Result<()> {
    let proxy = GlobalShortcuts::new().await?;
    let session = proxy.create_session().await?;

    let mut activated = proxy.receive_activated().await?;
    let mut deactivated = proxy.receive_deactivated().await?;

    loop {
        tokio::select! {
            // Incoming bind requests from the UI / startup code.
            msg = rx.recv() => {
                match msg {
                    Some(Msg::Bind { preferred }) => {
                        let trigger_ref = preferred.as_deref();
                        let shortcut = NewShortcut::new(SHORTCUT_ID, SHORTCUT_DESCRIPTION)
                            .preferred_trigger(trigger_ref);
                        // BindShortcuts REPLACES the session's binding list, so passing
                        // just our one shortcut (or none to unbind) is correct.
                        let shortcuts: Vec<NewShortcut> = if preferred.is_some() {
                            vec![shortcut]
                        } else {
                            // Unbind: bind an empty set.
                            vec![]
                        };
                        match proxy.bind_shortcuts(&session, &shortcuts, None).await {
                            Ok(_req) => {
                                eprintln!(
                                    "[hotkey/portal] bound shortcut preferred_trigger={:?}",
                                    preferred
                                );
                            }
                            Err(e) => {
                                eprintln!("[hotkey/portal] bind_shortcuts failed: {e:#}");
                            }
                        }
                    }
                    None => break, // channel closed -> app shutting down
                }
            }

            // Key press.
            Some(ev) = activated.next() => {
                if ev.shortcut_id() == SHORTCUT_ID {
                    let _ = cmd_tx.send(r#"{"type":"start_recording"}"#.to_string());
                }
            }

            // Key release (portal v2 only).
            Some(ev) = deactivated.next() => {
                if ev.shortcut_id() == SHORTCUT_ID {
                    let _ = cmd_tx.send(r#"{"type":"stop_recording"}"#.to_string());
                }
            }
        }
    }

    Ok(())
}

/// The portal expects triggers in the XDG "shortcuts" syntax, which
/// matches the Tauri accelerator syntax closely but uses lowercase
/// modifier names joined with `+`. Do a best-effort normalization so
/// the same hotkey strings users already have in settings keep working.
///
/// Examples:
///   "Space"               -> "space"
///   "F9"                  -> "F9"
///   "CmdOrCtrl+Shift+D"   -> "CTRL+SHIFT+d"
///   "Super+Space"         -> "LOGO+space"
fn normalize_trigger(s: &str) -> String {
    s.split('+')
        .map(|part| {
            let p = part.trim();
            match p.to_ascii_lowercase().as_str() {
                "cmd" | "command" | "cmdorctrl" | "meta" | "super" => "LOGO".to_string(),
                "ctrl" | "control" => "CTRL".to_string(),
                "alt" | "option" => "ALT".to_string(),
                "shift" => "SHIFT".to_string(),
                // Function keys stay uppercase, other single keys go lower.
                other if other.starts_with('f')
                    && other[1..].chars().all(|c| c.is_ascii_digit())
                    && !other[1..].is_empty() =>
                {
                    p.to_ascii_uppercase()
                }
                _ => p.to_ascii_lowercase(),
            }
        })
        .collect::<Vec<_>>()
        .join("+")
}
