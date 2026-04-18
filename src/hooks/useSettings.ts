/**
 * Settings: saved (persisted) vs pending (form) state for save bar and persistence.
 * savedSettings: last state known persisted. Updated on save completion or settings_saved / initial load.
 * pendingSettings: current form state. Screens edit this via setPendingSettings.
 * isDirty: true when pending !== saved so SaveBar can show.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { Device, ModelSize, Settings } from "../types";

const SETTINGS_KEYS: (keyof Settings)[] = [
  "app_language",
  "dictation_language",
  "hotkey",
  "theme",
  "vad_filter",
  "autopaste",
  "paste_shortcut",
  "save_history",
  "history_limit",
  "transcription_limit",
  "model_size",
  "device",
  "compute_type",
  "input_device",
  "log_level",
  "show_confidence",
  "show_timing",
  "show_detected_language",
  "window_width",
  "window_height",
  "window_x",
  "window_y",
  "first_run",
];

/** For save bar: exclude theme so theme-only changes don't show unsaved (theme applies immediately). */
function settingsEqualForSaveBar(a: Settings, b: Settings): boolean {
  for (const k of SETTINGS_KEYS) {
    if (k === "theme") continue;
    if (a[k] !== b[k]) return false;
  }
  return true;
}

export interface UseSettingsReturn {
  savedSettings: Settings;
  pendingSettings: Settings;
  setPendingSettings: (value: Settings | ((prev: Settings) => Settings)) => void;
  isDirty: boolean;
  save: (override?: Partial<Settings>) => Promise<void>;
  discard: () => void;
  getConfigPath: () => Promise<string | null>;
  requestStatus: () => void;
  /** True while a save is in progress */
  saving: boolean;
}

export function useSettings(initial: Settings): UseSettingsReturn {
  const [savedSettings, setSavedSettings] = useState<Settings>(initial);
  const [pendingSettings, setPendingSettings] = useState<Settings>(initial);
  const [saving, setSaving] = useState(false);

  const isDirty = useMemo(
    () => !settingsEqualForSaveBar(pendingSettings, savedSettings),
    [pendingSettings, savedSettings]
  );

  // Sync from sidecar ready: update saved only so we don't overwrite user's pending edits
  useEffect(() => {
    const unlisten = listen<{ type: string }>("sidecar_event", (event) => {
      const p = event.payload;
      if (p && typeof p === "object" && "type" in p && (p as { type: string }).type === "ready") {
        const r = p as { device?: string; model?: string; hotkey?: string; auto_paste?: boolean };
        setSavedSettings((s) => ({
          ...s,
          device: (r.device ?? s.device) as Device,
          model_size: (r.model ?? s.model_size) as ModelSize,
          ...(r.hotkey != null && r.hotkey !== "" ? { hotkey: r.hotkey } : {}),
          ...(typeof r.auto_paste === "boolean" ? { autopaste: r.auto_paste } : {}),
        }));
      }
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const getConfigPath = useCallback(async (): Promise<string | null> => {
    return invoke<string | null>("get_config_path").catch(() => null);
  }, []);

  const save = useCallback(async (override?: Partial<Settings>) => {
    const toSave = override ? { ...pendingSettings, ...override } : pendingSettings;
    setSaving(true);
    try {
      await invoke("update_settings", { settings: toSave });
      if (toSave.hotkey != null) {
        try {
          await invoke("register_hotkey_cmd", { hotkey: toSave.hotkey });
        } catch (e) {
          // Settings were persisted, but the hotkey couldn't be bound.
          // Surface a user-readable error so the UI can toast it.
          const raw = typeof e === "string" ? e : e instanceof Error ? e.message : String(e);
          throw new Error(`Couldn't bind hotkey "${toSave.hotkey}": ${raw}`);
        }
      }
      setSavedSettings(toSave);
      if (override) setPendingSettings(toSave);
    } finally {
      setSaving(false);
    }
  }, [pendingSettings]);

  const discard = useCallback(() => {
    setPendingSettings(savedSettings);
  }, [savedSettings]);

  const requestStatus = useCallback(() => {
    invoke("get_status").catch(() => {});
  }, []);

  return {
    savedSettings,
    pendingSettings,
    setPendingSettings,
    isDirty,
    save,
    discard,
    getConfigPath,
    requestStatus,
    saving,
  };
}
