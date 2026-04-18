/**
 * Shared types for dictate. See UI_SPEC.md.
 */

export type AppState =
  | "loading"
  | "ready"
  | "recording"
  | "transcribing"
  | "error";
export type ModelSize = "small" | "medium";
export type Device = "cpu" | "cuda";
export type ComputeType = "auto" | "int8" | "float16" | "int8_float16";
export type Theme = "auto" | "light" | "dark";
export type HistoryLimit = 50 | 100 | 500 | "unlimited";
export type TranscriptionLimit = 1 | 3 | 5 | 15 | 30;
export type PasteShortcut = "ctrl+v" | "ctrl+shift+v";
export type NavScreen = "general" | "advanced" | "model" | "history";
export type SessionType = "x11" | "wayland" | "unknown";

export type Language =
  | null // auto-detect
  | "en"
  | "es"
  | "fr"
  | "de"
  | "it"
  | "pt"
  | "nl"
  | "ru"
  | "zh"
  | "ja"
  | "ko"
  | "ar"
  | "hi";

export interface Settings {
  // General
  app_language: Language;
  dictation_language: Language;
  hotkey: string;

  // Appearance
  theme: Theme;

  // Model
  vad_filter: boolean;
  autopaste: boolean;
  paste_shortcut: PasteShortcut;
  save_history: boolean;
  history_limit: HistoryLimit;
  transcription_limit: TranscriptionLimit;

  // Advanced
  model_size: ModelSize;
  device: Device;
  compute_type: ComputeType;
  input_device: string | null; // null = system default
  log_level: "info" | "debug" | "verbose";
  show_confidence: boolean;
  show_timing: boolean;
  show_detected_language: boolean;

  // Window state
  window_width: number;
  window_height: number;
  window_x: number | null;
  window_y: number | null;

  // Meta
  first_run: boolean;
}

export interface Transcription {
  id: string; // uuid
  text: string;
  timestamp: string; // ISO 8601
  duration_ms: number | null; // length of recorded audio (ms)
  transcription_ms: number | null; // time model took to transcribe (ms)
  confidence: number | null; // 0–1, null if not recorded
  detected_language: string | null;
}

export interface SidecarStatus {
  cuda_available: boolean;
  model_loaded: boolean;
  queue_depth: number;
  last_transcription_ms: number | null;
  session_type: SessionType;
  pid: number | null;
  sidecar_version: string | null;
}

export type SidecarMessage =
  | {
      type: "ready";
      device: string;
      model: string;
      cuda_available: boolean;
      cuda_version?: string;
      session_type: SessionType;
      sidecar_version: string;
    }
  | { type: "recording_started" }
  | { type: "recording_stopped" }
  | { type: "transcribing"; queue_depth: number }
  | {
      type: "transcription_complete";
      text: string;
      duration_ms: number;
      transcription_ms?: number;
      confidence?: number;
      detected_language?: string;
    }
  | { type: "transcription_empty" }
  | { type: "settings_saved" }
  | { type: "model_loading" }
  | { type: "model_ready"; load_time_ms: number }
  | { type: "hotkey_mode"; mode: "tauri" | "evdev" | "none" }
  | { type: "error"; code: string; message: string };

/** Default settings for bootstrap and initial load. */
export const DEFAULT_SETTINGS: Settings = {
  // General
  app_language: null,
  dictation_language: null,
  hotkey: "Ctrl+Space",

  // Appearance
  theme: "auto",

  // Model
  vad_filter: true,
  autopaste: false,
  paste_shortcut: "ctrl+v",
  save_history: true,
  history_limit: 100,
  transcription_limit: 3,

  // Advanced
  model_size: "small",
  device: "cpu",
  compute_type: "auto",
  input_device: null,
  log_level: "info",
  show_confidence: false,
  show_timing: false,
  show_detected_language: false,

  // Window state
  window_width: 900,
  window_height: 600,
  window_x: null,
  window_y: null,

  // Meta
  first_run: true,
};
