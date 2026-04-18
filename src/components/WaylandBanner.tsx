/**
 * Wayland info banner.
 *
 * Shown when session_type === "wayland" on Linux.
 *
 * Copy depends on which hotkey backend is active:
 *   * "portal"         – XDG GlobalShortcuts portal: compositor confirms
 *                        the binding; push-to-talk on portal v2.
 *   * "gnome-fallback" – GNOME custom keybinding via gsettings; press-only,
 *                        so the hotkey toggles recording (start/stop).
 *   * "unavailable"    – No backend works on this compositor.
 */
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";

const WAYLAND_LEARN_MORE_URL =
  "https://github.com/your-org/dictate#linux--wayland";

type Backend = "legacy" | "portal" | "gnome-fallback" | "unavailable";

export function WaylandBanner() {
  const [backend, setBackend] = useState<Backend>("portal");

  useEffect(() => {
    invoke<Backend>("get_hotkey_backend")
      .then((b) => setBackend(b))
      .catch(() => {});
  }, []);

  const handleLearnMore = () => {
    openUrl(WAYLAND_LEARN_MORE_URL).catch(() => {});
  };

  let title = "Wayland session detected";
  let body =
    "Dictate uses the system shortcut portal on Wayland. When you set a hotkey your compositor (GNOME, KDE, Sway) will ask you to confirm it. Push-to-talk (hold to record) needs GNOME 45+, KDE Plasma 6+, or a recent Sway — on older compositors the hotkey toggles recording instead.";

  if (backend === "gnome-fallback") {
    title = "GNOME hotkey (toggle mode)";
    body =
      "Dictate registers your hotkey through GNOME's keyboard shortcut system (gsettings). GNOME only sends key-press events to custom shortcuts, so the hotkey toggles recording (press once to start, press again to stop) instead of push-to-talk. The binding will appear in Settings → Keyboard → Custom Shortcuts as 'Dictate toggle'.";
  } else if (backend === "unavailable") {
    title = "Global hotkey unavailable";
    body =
      "This Wayland compositor doesn't expose the XDG GlobalShortcuts portal and isn't GNOME, so Dictate can't register a global hotkey. Consider running Dictate via Flatpak, or bind a hotkey manually in your compositor's keyboard settings to invoke 'dictate --toggle'.";
  }

  return (
    <div
      className="mb-4 rounded-input border border-accent/30 bg-accent/[0.06] px-4 py-3 flex items-start gap-3"
      role="status"
    >
      <span className="text-accent text-base flex-shrink-0" aria-hidden>
        ℹ
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary">{title}</p>
        <p className="text-xs text-text-muted leading-normal mt-1">{body}</p>
        <button
          type="button"
          onClick={handleLearnMore}
          className="text-xs text-accent hover:text-accent-hover hover:underline mt-2 text-left"
        >
          Learn more
        </button>
      </div>
    </div>
  );
}
