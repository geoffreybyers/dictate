/**
 * Root settings panel: header, status bar, settings form, footer.
 */
import { useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { useAppState } from "../hooks/useAppState";
import { useSettings } from "../hooks/useSettings";
import { DEFAULT_SETTINGS } from "../types";
import { StatusBar } from "./StatusBar";
import { WaylandBanner } from "./WaylandBanner";
import { ModelSelect } from "./settings/ModelSelect";
import { DeviceSelect } from "./settings/DeviceSelect";
import { LanguageSelect } from "./settings/LanguageSelect";
import { HotkeyCapture } from "./settings/HotkeyCapture";
import { VadToggle } from "./settings/VadToggle";
import { AutoPasteToggle } from "./settings/AutoPasteToggle";

export function SettingsPanel() {
  const appState = useAppState();
  const {
    pendingSettings,
    setPendingSettings,
    isDirty,
    save,
    requestStatus,
    saving,
  } = useSettings(DEFAULT_SETTINGS);
  const [displayResult, setDisplayResult] = useState<{ text: string; durationMs: number } | null>(null);
  const [showSavedConfirmation, setShowSavedConfirmation] = useState(false);
  const savedConfirmationTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastResultTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    requestStatus();
  }, [requestStatus]);

  useEffect(() => {
    if (appState.lastResult) {
      setDisplayResult(appState.lastResult);
      if (lastResultTimeout.current) clearTimeout(lastResultTimeout.current);
      lastResultTimeout.current = setTimeout(() => {
        setDisplayResult(null);
        lastResultTimeout.current = null;
      }, 3000);
    }
    return () => {
      if (lastResultTimeout.current) clearTimeout(lastResultTimeout.current);
    };
  }, [appState.lastResult]);

  useEffect(() => {
    return () => {
      if (savedConfirmationTimeout.current) clearTimeout(savedConfirmationTimeout.current);
    };
  }, []);

  const handleSave = async () => {
    await save();
    setShowSavedConfirmation(true);
    if (savedConfirmationTimeout.current) clearTimeout(savedConfirmationTimeout.current);
    savedConfirmationTimeout.current = setTimeout(() => {
      setShowSavedConfirmation(false);
      savedConfirmationTimeout.current = null;
    }, 1500);
  };

  const handleClose = () => {
    getCurrentWindow().hide();
  };

  const isWayland = typeof navigator !== "undefined" && /Linux/.test(navigator.userAgent) && appState.sessionType === "wayland";

  const statusDot =
    appState.status === "recording"
      ? "bg-recording"
      : appState.status === "transcribing"
        ? "bg-warning"
        : appState.status === "error"
          ? "bg-error"
          : appState.status === "loading"
            ? "bg-text-muted"
            : "bg-success";

  return (
    <div className="min-h-screen bg-background text-text-primary font-sans flex flex-col rounded-panel shadow-panel overflow-hidden panel-enter">
      <header
        className="h-12 px-panel flex items-center justify-between border-b border-border flex-shrink-0"
        data-tauri-drag-region
      >
        <div className="flex items-center gap-2" data-tauri-drag-region>
          <span className={`w-3 h-3 rounded-full ${statusDot}`} />
          <span className="text-base font-medium">dictate</span>
        </div>
        <button
          type="button"
          onClick={handleClose}
          className="w-7 h-7 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-surface-hover rounded"
          aria-label="Close"
        >
          ✕
        </button>
      </header>

      <StatusBar
        status={appState.status}
        queueDepth={appState.queueDepth}
        hotkey={pendingSettings.hotkey}
        error={appState.error}
        lastResult={displayResult}
      />

      <main
        className={`flex-1 overflow-auto px-panel py-gap-lg space-y-gap-lg transition-opacity duration-200 ease-in-out ${
          appState.status === "loading" ? "opacity-40 pointer-events-none" : ""
        }`}
      >
        {pendingSettings.first_run === true && (
          <div
            className="mb-gap-lg rounded-input border border-accent/20 bg-accent/10 px-4 py-3 flex items-start justify-between gap-3"
            role="status"
          >
            <div>
              <p className="text-sm font-medium text-text-primary">👋 Welcome to dictate</p>
              <p className="text-xs text-text-secondary mt-1">
                Configure your settings below, then hold{" "}
                <kbd className="bg-surface-hover border border-border rounded px-1.5 py-0.5 font-mono text-xs">
                  {pendingSettings.hotkey}
                </kbd>{" "}
                to start.
              </p>
            </div>
            <button
              type="button"
              onClick={() => save({ first_run: false })}
              className="flex-shrink-0 w-7 h-7 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-surface-hover rounded"
              aria-label="Dismiss welcome"
            >
              ✕
            </button>
          </div>
        )}
        {isWayland && <WaylandBanner />}

        <ModelSelect
          value={pendingSettings.model_size}
          onChange={(v) => setPendingSettings((s) => ({ ...s, model_size: v }))}
        />
        <DeviceSelect
          value={pendingSettings.device}
          cudaAvailable={appState.cudaAvailable}
          onChange={(v) => setPendingSettings((s) => ({ ...s, device: v }))}
        />
        <LanguageSelect
          value={pendingSettings.dictation_language}
          onChange={(v) => setPendingSettings((s) => ({ ...s, dictation_language: v }))}
        />
        <HotkeyCapture
          value={pendingSettings.hotkey}
          onChange={(v) => setPendingSettings((s) => ({ ...s, hotkey: v }))}
        />
        <VadToggle
          value={pendingSettings.vad_filter}
          onChange={(v) => setPendingSettings((s) => ({ ...s, vad_filter: v }))}
        />
        <AutoPasteToggle
          value={pendingSettings.autopaste}
          onChange={(v) => setPendingSettings((s) => ({ ...s, autopaste: v }))}
        />
      </main>

      <footer className="h-[52px] px-panel flex items-center justify-between border-t border-border flex-shrink-0">
        <span className="text-xs text-text-muted font-mono">
          ○ {pendingSettings.device} · {pendingSettings.device === "cuda" ? "float16" : "int8"} · {pendingSettings.model_size}
        </span>
        {showSavedConfirmation ? (
          <span className="text-sm text-success">Saved ✓</span>
        ) : (
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !isDirty}
            className="h-8 px-4 rounded-input text-sm font-medium disabled:bg-surface disabled:text-text-muted disabled:cursor-not-allowed bg-accent text-on-accent hover:bg-accent-hover transition-opacity duration-150"
          >
            Save Changes
          </button>
        )}
      </footer>
    </div>
  );
}
