/**
 * Advanced settings screen. No save bar — all controls apply immediately or are read-only.
 */
import { useCallback, useEffect, useState } from "react";
import * as Select from "@radix-ui/react-select";
import * as Switch from "@radix-ui/react-switch";
import { ChevronDown, Loader2 } from "lucide-react";
import { getVersion, getTauriVersion } from "@tauri-apps/api/app";
import { appConfigDir, appLogDir, join } from "@tauri-apps/api/path";
import { open } from "@tauri-apps/plugin-shell";
import { openPath } from "@tauri-apps/plugin-opener";
import { invoke } from "@tauri-apps/api/core";
import { useSettingsContext } from "../../contexts/SettingsContext";
import { useAppState } from "../../hooks/useAppState";
import { GITHUB_REPO } from "../../lib/constants";
import type { PasteShortcut, TranscriptionLimit } from "../../types";
import { PathDisplay } from "../settings/PathDisplay";
import { SettingGroup } from "../settings/SettingGroup";
import { SettingRow } from "../settings/SettingRow";

const LOG_LEVEL_OPTIONS: { value: "info" | "debug" | "verbose"; label: string }[] = [
  { value: "info", label: "Info" },
  { value: "debug", label: "Debug" },
  { value: "verbose", label: "Verbose" },
];

const TRANSCRIPTION_LIMIT_OPTIONS: { value: TranscriptionLimit; label: string }[] = [
  { value: 1, label: "1 minute" },
  { value: 3, label: "3 minutes" },
  { value: 5, label: "5 minutes" },
  { value: 15, label: "15 minutes" },
  { value: 30, label: "30 minutes" },
];

const WEBSOCKET_PORT_DEFAULT = "39821";

const INVOKE_TIMEOUT_MS = 5000;

function invokeWithTimeout<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return Promise.race([
    args != null ? invoke<T>(cmd, args) : invoke<T>(cmd),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("timeout")), INVOKE_TIMEOUT_MS)
    ),
  ]);
}

export function AdvancedScreen() {
  const { savedSettings, save, getConfigPath, requestStatus } = useSettingsContext();
  const appState = useAppState();

  useEffect(() => {
    requestStatus();
  }, [requestStatus]);

  const [restarting, setRestarting] = useState(false);
  const [appVersion, setAppVersion] = useState<string>("—");
  const [tauriVersion, setTauriVersion] = useState<string>("—");
  const [platform, setPlatform] = useState<string>("—");
  const [osVersion, setOsVersion] = useState<string>("—");
  const [appHomePath, setAppHomePath] = useState<string>("");

  useEffect(() => {
    getVersion().then(setAppVersion).catch(() => setAppVersion("—"));
    getTauriVersion().then(setTauriVersion).catch(() => setTauriVersion("—"));
    setPlatform(
      typeof navigator !== "undefined"
        ? navigator.platform || navigator.userAgent?.split(" ").slice(-2).join(" ") || "—"
        : "—"
    );
    invokeWithTimeout<string>("get_os_version")
      .then(setOsVersion)
      .catch(() => setOsVersion("—"));
    appConfigDir().then(setAppHomePath).catch(() => setAppHomePath(""));
  }, []);

  const handleRestartSidecar = useCallback(async () => {
    setRestarting(true);
    try {
      await invokeWithTimeout<unknown>("restart_sidecar");
    } catch {
      setRestarting(false);
    }
  }, []);

  useEffect(() => {
    if (restarting && appState.modelReady) setRestarting(false);
  }, [restarting, appState.modelReady]);

  const handleOpenSidecarLogs = useCallback(async () => {
    const configPath = await getConfigPath();
    if (!configPath) return;
    const logPath = `${configPath.replace(/\/?$/, "")}/app.log`;
    await openPath(logPath);
  }, [getConfigPath]);

  const handleOpenAppLogs = useCallback(async () => {
    try {
      const logDir = await appLogDir();
      const logPath = await join(logDir, "dictate.log");
      await open(logPath);
    } catch {
      // ignore
    }
  }, []);

  const handleOpenGitHub = useCallback(() => {
    open(`https://github.com/${GITHUB_REPO}/dictate/issues`).catch(() => {});
  }, []);

  const sidecarStatusLabel =
    appState.status === "loading"
      ? "Restarting..."
      : appState.modelReady
        ? "Running"
        : "Stopped";
  const sidecarStatusVariant =
    appState.status === "loading" ? "amber" : appState.modelReady ? "green" : "red";

  return (
    <div className="flex flex-col gap-8" style={{ gap: "32px" }}>
      <SettingGroup title="Transcription">
        <SettingRow
          label="Autopaste"
          helper="Automatically paste transcription result at cursor position"
          layout="inline"
        >
          <Switch.Root
            checked={savedSettings.autopaste}
            onCheckedChange={(checked) => save({ ...savedSettings, autopaste: checked })}
            className="relative w-10 h-[22px] rounded-full border border-border bg-surface-hover data-[state=checked]:bg-accent data-[state=checked]:border-accent focus:outline-none focus:ring-2 focus:ring-border-focus cursor-pointer"
            aria-label="Autopaste"
          >
            <Switch.Thumb className="block w-[18px] h-[18px] rounded-full bg-background border border-border translate-x-0.5 data-[state=checked]:translate-x-[18px] transition-transform duration-200" />
          </Switch.Root>
        </SettingRow>
        {savedSettings.autopaste && (
          <>
            <SettingRow
              label="Paste Shortcut"
              helper="Key combination used to paste transcribed text"
              layout="stacked"
            >
              <Select.Root
                value={savedSettings.paste_shortcut}
                onValueChange={(v) =>
                  save({ ...savedSettings, paste_shortcut: v as PasteShortcut })
                }
              >
                <Select.Trigger
                  className="w-full h-9 bg-surface border border-border rounded-lg text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus"
                  aria-label="Paste Shortcut"
                >
                  <Select.Value />
                  <Select.Icon className="text-text-muted">
                    <span aria-hidden>▾</span>
                  </Select.Icon>
                </Select.Trigger>
                <Select.Portal>
                  <Select.Content
                    className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 min-w-[var(--radix-select-trigger-width)] text-text-primary"
                    position="popper"
                    sideOffset={4}
                  >
                    <Select.Viewport className="p-1">
                      <Select.Item
                        value="ctrl+v"
                        className="text-sm !text-text-primary px-3 py-2 rounded cursor-pointer outline-none focus:bg-surface-hover data-[highlighted]:bg-surface-hover"
                      >
                        <Select.ItemText>Ctrl+V</Select.ItemText>
                      </Select.Item>
                      <Select.Item
                        value="ctrl+shift+v"
                        className="text-sm !text-text-primary px-3 py-2 rounded cursor-pointer outline-none focus:bg-surface-hover data-[highlighted]:bg-surface-hover"
                      >
                        <Select.ItemText>Ctrl+Shift+V</Select.ItemText>
                      </Select.Item>
                    </Select.Viewport>
                  </Select.Content>
                </Select.Portal>
              </Select.Root>
            </SettingRow>
            <p className="text-text-muted mt-1" style={{ fontSize: "11px" }}>
              ℹ Autopaste simulates the selected shortcut after copying. Requires accessibility
              permissions on macOS.
            </p>
          </>
        )}

        <SettingRow
          label="Max Recording Length"
          helper="Automatically stop recording after this duration"
          layout="stacked"
        >
          <Select.Root
            value={String(savedSettings.transcription_limit)}
            onValueChange={(v) =>
              save({
                ...savedSettings,
                transcription_limit: Number(v) as TranscriptionLimit,
              })
            }
          >
            <Select.Trigger
              className="w-full h-9 bg-surface border border-border rounded-lg text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus"
              aria-label="Max Recording Length"
            >
              <Select.Value />
              <Select.Icon className="text-text-muted">
                <span aria-hidden>▾</span>
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content
                className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 min-w-[var(--radix-select-trigger-width)] text-text-primary"
                position="popper"
                sideOffset={4}
              >
                <Select.Viewport className="p-1">
                  {TRANSCRIPTION_LIMIT_OPTIONS.map((opt) => (
                    <Select.Item
                      key={opt.value}
                      value={String(opt.value)}
                      className="text-sm !text-text-primary px-3 py-2 rounded cursor-pointer outline-none focus:bg-surface-hover data-[highlighted]:bg-surface-hover"
                    >
                      <Select.ItemText>{opt.label}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </SettingRow>

        <SettingRow
          label="Show confidence score"
          helper="Display per-transcription confidence from the model"
          layout="inline"
        >
          <Switch.Root
            checked={savedSettings.show_confidence}
            onCheckedChange={(checked) => save({ ...savedSettings, show_confidence: checked })}
            className="relative w-10 h-[22px] rounded-full border border-border bg-surface-hover data-[state=checked]:bg-accent data-[state=checked]:border-accent focus:outline-none focus:ring-2 focus:ring-border-focus cursor-pointer"
            aria-label="Show confidence score"
          >
            <Switch.Thumb className="block w-[18px] h-[18px] rounded-full bg-background border border-border translate-x-0.5 data-[state=checked]:translate-x-[18px] transition-transform duration-200" />
          </Switch.Root>
        </SettingRow>
        <SettingRow
          label="Show transcription timing"
          helper="Display how long each transcription took"
          layout="inline"
        >
          <Switch.Root
            checked={savedSettings.show_timing}
            onCheckedChange={(checked) => save({ ...savedSettings, show_timing: checked })}
            className="relative w-10 h-[22px] rounded-full border border-border bg-surface-hover data-[state=checked]:bg-accent data-[state=checked]:border-accent focus:outline-none focus:ring-2 focus:ring-border-focus cursor-pointer"
            aria-label="Show transcription timing"
          >
            <Switch.Thumb className="block w-[18px] h-[18px] rounded-full bg-background border border-border translate-x-0.5 data-[state=checked]:translate-x-[18px] transition-transform duration-200" />
          </Switch.Root>
        </SettingRow>
        <SettingRow
          label="Show detected language"
          helper="When using Auto-detect, display the identified language"
          layout="inline"
        >
          <Switch.Root
            checked={savedSettings.show_detected_language}
            onCheckedChange={(checked) =>
              save({ ...savedSettings, show_detected_language: checked })
            }
            className="relative w-10 h-[22px] rounded-full border border-border bg-surface-hover data-[state=checked]:bg-accent data-[state=checked]:border-accent focus:outline-none focus:ring-2 focus:ring-border-focus cursor-pointer"
            aria-label="Show detected language"
          >
            <Switch.Thumb className="block w-[18px] h-[18px] rounded-full bg-background border border-border translate-x-0.5 data-[state=checked]:translate-x-[18px] transition-transform duration-200" />
          </Switch.Root>
        </SettingRow>
      </SettingGroup>

      <SettingGroup title="Application">
        <SettingRow label="WebSocket port" layout="inline">
          <PathDisplay
            value={WEBSOCKET_PORT_DEFAULT}
            copyLabel="Copy port"
          />
        </SettingRow>

        <SettingRow label="Sidecar process" layout="inline">
          <div className="flex items-center gap-2 shrink-0">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                sidecarStatusVariant === "green"
                  ? "bg-success/20 text-success"
                  : sidecarStatusVariant === "red"
                    ? "bg-error/20 text-error"
                    : "bg-warning/20 text-warning"
              }`}
            >
              {sidecarStatusLabel}
            </span>
            {appState.pid != null && appState.modelReady && (
              <span className="text-sm font-mono text-text-muted">PID {appState.pid}</span>
            )}
          </div>
        </SettingRow>

        <SettingRow
          label="Restart sidecar"
          helper="Force restart the Python transcription process"
          layout="inline"
        >
          <button
            type="button"
            disabled={restarting}
            onClick={handleRestartSidecar}
            className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover border border-border focus:outline-none focus:ring-2 focus:ring-border-focus disabled:opacity-50 inline-flex items-center gap-2"
          >
            {restarting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Restarting...
              </>
            ) : (
              "Restart"
            )}
          </button>
        </SettingRow>

        <SettingRow label="Log level" layout="stacked">
          <Select.Root
            value={savedSettings.log_level}
            onValueChange={(v) =>
              save({ ...savedSettings, log_level: v as "info" | "debug" | "verbose" })
            }
          >
            <Select.Trigger className="inline-flex items-center justify-between gap-2 h-9 min-w-[140px] px-3 rounded-lg border border-border bg-surface text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus">
              <Select.Value />
              <Select.Icon className="text-text-muted">
                <ChevronDown className="w-4 h-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 text-text-primary">
                <Select.Viewport className="p-1">
                  {LOG_LEVEL_OPTIONS.map((opt) => (
                    <Select.Item
                      key={opt.value}
                      value={opt.value}
                      className="text-sm !text-text-primary px-2 py-1.5 rounded-md outline-none data-[highlighted]:bg-surface-hover data-[state=checked]:bg-accent/10"
                    >
                      <Select.ItemText>{opt.label}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </SettingRow>

        <SettingRow label="Open sidecar logs" layout="inline">
          <button
            type="button"
            onClick={handleOpenSidecarLogs}
            className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover border border-border focus:outline-none focus:ring-2 focus:ring-border-focus"
          >
            Open Logs
          </button>
        </SettingRow>
      </SettingGroup>

      <SettingGroup title="App Info">
        <SettingRow
          label="Open app logs"
          helper="View application and error logs"
          layout="inline"
        >
          <button
            type="button"
            onClick={handleOpenAppLogs}
            className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover border border-border focus:outline-none focus:ring-2 focus:ring-border-focus"
          >
            Open Logs
          </button>
        </SettingRow>
        <SettingRow
          label="App home directory"
          helper="Configuration and model cache location"
          layout="stacked"
        >
          <PathDisplay value={appHomePath} placeholder="—" copyLabel="Copy path" />
        </SettingRow>
        <SettingRow label="Report bug or send feedback" layout="inline">
          <button
            type="button"
            onClick={handleOpenGitHub}
            className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover border border-border focus:outline-none focus:ring-2 focus:ring-border-focus"
          >
            Open GitHub
          </button>
        </SettingRow>
      </SettingGroup>

      <SettingGroup title="Session Info">
        <SettingRow label="Session type" layout="inline">
          <span className="text-sm font-mono text-text-muted">{appState.sessionType}</span>
        </SettingRow>
        <SettingRow label="App version" layout="inline">
          <span className="text-sm font-mono text-text-muted">{appVersion}</span>
        </SettingRow>
        <SettingRow label="Tauri version" layout="inline">
          <span className="text-sm font-mono text-text-muted">{tauriVersion}</span>
        </SettingRow>
        <SettingRow label="Platform" layout="inline">
          <span className="text-sm font-mono text-text-muted">{platform}</span>
        </SettingRow>
        <SettingRow label="OS version" layout="inline">
          <span className="text-sm font-mono text-text-muted">{osVersion}</span>
        </SettingRow>
        <SettingRow label="Sidecar version" layout="inline">
          <span className="text-sm font-mono text-text-muted">
            {appState.sidecarVersion ?? "—"}
          </span>
        </SettingRow>
      </SettingGroup>
    </div>
  );
}
