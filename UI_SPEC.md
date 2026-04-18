# dictate — UI Specification

The reference for the desktop app's window layout, navigation, and settings surfaces. This doc describes what is actually implemented in `src/`; it is not a forward-looking roadmap.

## Window

- Tauri v2 main window, label `main`.
- Default size 900×600, min 740×480, resizable.
- Frameless (`decorations: false`) — custom header draws minimize/maximize/close. The full header (except the three window-control buttons) is a drag region.
- Window size and position are persisted to `settings.json` (`window_width`, `window_height`, `window_x`, `window_y`) and restored on launch. Off-screen positions fall back to centered.

## Layout

```
┌─────────────────────────────────────────────────────┐
│                                    [─] [□] [✕]      │   Header 52px (drag region)
├────────────────────┬────────────────────────────────┤
│  ⚙ General          │                                │
│  </> Advanced       │                                │
│  🤖 Model            │    Content area (scrolls)      │
│  💬 History          │                                │
│                     │                                │
│  [sidebar status]   │                                │
└────────────────────┴────────────────────────────────┘
   220px fixed           flex-1
```

## Header (`src/components/layout/Header.tsx`)

Empty drag region with three native-styled controls on the right: minimize, maximize/restore, close. Double-click on the drag region toggles maximize.

## Left navigation (`src/components/layout/LeftNav.tsx`)

Fixed 220px width. Flat list of four items (no section headers). Active item is indicated by a 2px accent-colored left border and elevated surface background.

| Item | Icon | Screen |
|---|---|---|
| General | `Settings` | `GeneralScreen.tsx` |
| Advanced | `Code2` | `AdvancedScreen.tsx` |
| Model | `Bot` | `ModelScreen.tsx` |
| History | `MessageSquare` | `HistoryScreen.tsx` |

Default active screen on launch: **General**. Active screen is component state (not persisted).

A footer (`SidebarStatus.tsx`) below the nav list shows current status: `Hold [hotkey] to transcribe`, `● Recording…`, `⏳ Transcribing…`, `✓ Copied to clipboard · 1.4s`, or `⚠ error`.

## Content area & save behavior

Each screen is composed of `SettingGroup` → `SettingRow` elements. Settings screens (General, Model, Advanced) use an explicit save model: when any field differs from saved state, a `SaveBar` slides up from the bottom of the content area with `[Discard] [Save]` actions. History has no save bar.

Device changes on Model are handled specially — saving a new device triggers a sidecar restart.

## Settings screens (abridged)

The full set of settings lives in `src/types/index.ts` under the `Settings` interface. Each screen wires those fields to controls.

### General
- App Language, Dictation Language (dropdowns; `null` = auto-detect for dictation)
- Push-to-Talk Hotkey (HotkeyCapture — requires modifier when the Space key is used)
- Theme (Auto / Light / Dark — Auto reads the OS color scheme on Linux via `org.freedesktop.portal.Settings`)
- History: Save History toggle, History Limit, Clear All

### Model
- Model Size (small / medium)
- Compute Type (auto / int8 / float16 / int8_float16)
- Model Cache Directory (read-only path + copy)
- Hardware: Device (cpu / cuda), CUDA Version (read-only), Microphone input selector

### Advanced
- Transcription: Autopaste toggle, Paste Shortcut (ctrl+v / ctrl+shift+v — only shown when autopaste is on), Max Recording Length, Show confidence score, Show transcription timing, Show detected language
- App Info: Open Logs button, App Home Directory (read-only path), Report Bug (opens GitHub issues)
- Session Info: session type, app version, Tauri version, platform, OS version, Python sidecar version

### History
Grouped list of saved transcriptions by day (Today / Yesterday / absolute date). Each row shows timestamp, full text, and per-row `Copy` / `Delete` buttons. Optional metadata row (`92% confidence · 1.4s · en`) appears when the corresponding Advanced toggles are enabled. Clear All is in the screen header.

Empty state: `No transcriptions yet — Hold [hotkey] to record your first transcription.` When Save History is disabled, a separate empty state points the user back to General.

## Wayland banner

When the sidecar reports `session_type === "wayland"`, a banner appears on each Settings screen (not History) describing the detected hotkey backend (`portal` / `gnome-fallback` / `unavailable`). Copy is driven by the `get_hotkey_backend` Tauri command. See ARCHITECTURE.md for the backend selection rules.

## First run

On first launch (`first_run: true` in settings), the General screen shows a dismissible welcome banner above all groups. Dismissing sets `first_run: false`.

## Theme

Auto theme watches the OS color scheme. On Linux this uses the `org.freedesktop.portal.Settings` `ColorScheme` key; on macOS/Windows it uses `dark-light`. Theme changes apply live without restart. Explicit Light/Dark bypass the watcher.

## Component directory

```
src/components/
├── layout/           # Header, LeftNav, ContentArea, SaveBar, SidebarStatus, Toast
├── screens/          # GeneralScreen, ModelScreen, AdvancedScreen, HistoryScreen
├── settings/         # SettingGroup, SettingRow, HotkeyCapture, PathDisplay, etc.
├── transcriptions/   # TranscriptionItem
├── banners/          # WelcomeBanner, WaylandBanner
└── ui/               # shadcn/ui primitives
```
