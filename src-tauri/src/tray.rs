//! Tray icon and menu. Left-click shows tray menu with "Open Dictate" and "Quit Dictate".
//! Open Dictate brings the main window to the front. Tray icon switches by status (see update_icon_for_status).

use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Manager,
};
use tauri_plugin_positioner::on_tray_event;

const SETTINGS_WINDOW_LABEL: &str = "main";
const TRAY_ID: &str = "main";
const MENU_ID_OPEN: &str = "tray-open";
const MENU_ID_QUIT: &str = "tray-quit";

/// Create tray icon and set up menu (Open Dictate, Quit Dictate). No auto-hide on blur so the window can be dragged.
pub fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let icon = load_tray_icon("tray-idle")?;
    // On Linux (libappindicator) the tray icon often won't appear unless a menu is set.
    let open_item = MenuItem::with_id(app, MENU_ID_OPEN, "Open Dictate", true, None::<&str>)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
    let quit_item = MenuItem::with_id(app, MENU_ID_QUIT, "Quit Dictate", true, None::<&str>)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
    let menu = Menu::with_items(app, &[&open_item, &quit_item])
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;

    TrayIconBuilder::with_id(TRAY_ID)
        .menu(&menu)
        .icon(icon)
        .tooltip("dictate")
        .show_menu_on_left_click(true)
        .on_menu_event(move |app, event| {
            if event.id().as_ref() == MENU_ID_OPEN {
                bring_app_to_front(app);
            } else if event.id().as_ref() == MENU_ID_QUIT {
                app.exit(0);
            }
        })
        .on_tray_icon_event(|tray, event| {
            on_tray_event(tray.app_handle(), &event);
        })
        .build(app)?;

    Ok(())
}

/// Bring the main window to the front (show and focus). Used when user picks "Open Dictate" from tray menu.
/// Does not move the window; on many desktops, focusing can switch to the workspace where the window is.
fn bring_app_to_front(app: &AppHandle) {
    if let Some(win) = app.get_webview_window(SETTINGS_WINDOW_LABEL) {
        let _ = win.show();
        let _ = win.set_focus();
    }
}

fn load_tray_icon(state: &str) -> Result<Image<'static>, Box<dyn std::error::Error + Send + Sync>> {
    // Tray icons: tray-idle, tray-recording, tray-working, tray-error.
    // Fallback to app icon if state-specific file fails or is placeholder.
    let bytes: &'static [u8] = match state {
        "tray-idle" => include_bytes!("../icons/tray-idle.png"),
        "tray-recording" => include_bytes!("../icons/tray-recording.png"),
        "tray-working" => include_bytes!("../icons/tray-working.png"),
        "tray-error" => include_bytes!("../icons/tray-error.png"),
        _ => include_bytes!("../icons/Square44x44Logo.png"),
    };
    Image::from_bytes(bytes).map_err(|e| e.into())
}

/// Update tray icon from app status. Frontend calls set_tray_status with status string.
/// Maps: idle → tray-idle, recording → tray-recording, transcribing → tray-working, error → tray-error.
pub fn update_icon_for_status(app: &AppHandle, status: &str) {
    let icon_name = match status {
        "loading" => "tray-working",
        "ready" => "tray-idle",
        "recording" => "tray-recording",
        "transcribing" => "tray-working",
        "error" => "tray-error",
        _ => "tray-idle",
    };
    if let Ok(icon) = load_tray_icon(icon_name) {
        if let Some(tray) = app.tray_by_id(TRAY_ID) {
            let _ = tray.set_icon(Some(icon));
        }
    }
}
