# Debugging the dictate app

## Viewing logs and inspecting the UI

### 1. Run in development mode

From the project root:

```bash
npm run tauri dev
```

- **Rust (Tauri) logs** go to the **terminal** where you ran the command (stdout/stderr).
- **Frontend (React) logs** appear in the **webview DevTools console** (see below).

### 2. Open WebView DevTools (frontend / React)

With the app running (dev or built), open the developer tools on the app window:

- **Windows / Linux:** `Ctrl + Shift + I`
- **macOS:** `Cmd + Option + I`

Or **right‑click** inside the app window → **Inspect** / **Inspect Element**.

Use the **Console** tab to see:

- `console.log` / `console.warn` / `console.error` from the frontend
- JavaScript errors (e.g. if the UI freezes due to an uncaught exception or infinite loop)

Use the **Performance** or **Profiler** tab to see if the main thread is busy (e.g. long tasks or many re-renders).

### 3. Optional: verbose logging on the Developer screen

If the app “freezes” when you open the **Developer** settings tab, you can enable extra console logs for that screen:

1. Open DevTools (e.g. `Ctrl + Shift + I`) **before** opening the Developer tab.
2. In the Console, run:

   ```js
   localStorage.setItem('dictate:debugDeveloper', '1')
   ```

3. Reload the app (or navigate away and back to Developer).
4. Go to the **Developer** tab and watch the Console for messages like `[DeveloperScreen] …`.
5. When done, turn it off:

   ```js
   localStorage.removeItem('dictate:debugDeveloper')
   ```

Interpretation:

- **Many `[DeveloperScreen] render`** → likely a render loop.
- **One `render`, then e.g. `useEffect: …` and nothing after** → that effect or an invoke may be hanging or very slow.

### 4. Log files

- **Developer → Open Logs** opens the sidecar log (e.g. `…/app.log` next to the config).
- **General → Open app logs** opens the Tauri app log (e.g. `dictate.log` in the app log directory).

Use these for backend/sidecar issues; for frontend freezes, DevTools Console and optional `dictate:debugDeveloper` logs are more useful.

### 5. Auto-open DevTools in dev (optional)

To have DevTools open automatically when running `npm run tauri dev`, you can open them from Rust in debug builds. In `src-tauri/src/lib.rs`, inside the `.setup()` closure, add:

```rust
#[cfg(debug_assertions)]
if let Some(win) = app.get_webview_window("main") {
    let _ = win.open_devtools();
}
```

Remove or disable this when you are done debugging.
