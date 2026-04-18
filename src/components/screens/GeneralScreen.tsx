/**
 * General screen: welcome banner, Hotkey + Languages, Appearance, History.
 */
import * as Select from "@radix-ui/react-select";
import * as Switch from "@radix-ui/react-switch";
import { useAppState } from "../../hooks/useAppState";
import { useSettingsContext } from "../../contexts/SettingsContext";
import {
  LANGUAGE_OPTIONS,
  languageToSelectValue,
  selectValueToLanguage,
} from "../../constants/languages";
import type { HistoryLimit, Theme } from "../../types";
import { HotkeyCapture } from "../settings/HotkeyCapture";
import { SettingGroup } from "../settings/SettingGroup";
import { SettingRow } from "../settings/SettingRow";
import { WaylandBanner } from "../WaylandBanner";

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: "auto", label: "Auto (follows system)" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

const HISTORY_LIMIT_OPTIONS: { value: HistoryLimit; label: string }[] = [
  { value: 50, label: "50 items" },
  { value: 100, label: "100 items" },
  { value: 500, label: "500 items" },
  { value: "unlimited", label: "Unlimited" },
];

export function GeneralScreen() {
  const { pendingSettings, savedSettings, setPendingSettings, save } = useSettingsContext();
  const appState = useAppState();

  const handleThemeChange = (value: Theme) => {
    setPendingSettings((s) => ({ ...s, theme: value }));
    save({ theme: value });
  };

  const saveHistoryOn = pendingSettings.save_history;
  const isWayland = appState.sessionType === "wayland";

  return (
    <div className="flex flex-col gap-8" style={{ gap: "32px" }}>
      {savedSettings.first_run && (
        <div
          className="rounded-input border border-accent/20 bg-accent/10 px-4 py-3 flex items-start justify-between gap-3"
          role="status"
        >
          <div>
            <p className="text-sm font-medium text-text-primary">Welcome to dictate</p>
            <p className="text-xs text-text-secondary mt-1">
              Configure your settings below, then hold{" "}
              <kbd className="bg-surface-hover border border-border rounded px-1.5 py-0.5 font-mono text-xs">
                {savedSettings.hotkey}
              </kbd>{" "}
              to start.
            </p>
          </div>
          <button
            type="button"
            onClick={() => save({ ...savedSettings, first_run: false })}
            className="flex-shrink-0 w-7 h-7 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-surface-hover rounded"
            aria-label="Dismiss welcome"
          >
            ✕
          </button>
        </div>
      )}
      {isWayland && <WaylandBanner />}

      <SettingGroup title="General Settings">
        <SettingRow
          label="Push-to-Talk Hotkey"
          helper="Hold this key to record. Release to transcribe."
          layout="stacked"
        >
          <HotkeyCapture
            value={pendingSettings.hotkey}
            onChange={(v) => setPendingSettings((s) => ({ ...s, hotkey: v }))}
            hideLabel
          />
        </SettingRow>

        <SettingRow
          label="App Language"
          helper="Language for the dictate interface"
          layout="stacked"
        >
          <Select.Root
            value={languageToSelectValue(pendingSettings.app_language)}
            onValueChange={(v) =>
              setPendingSettings((s) => ({ ...s, app_language: selectValueToLanguage(v) }))
            }
          >
            <Select.Trigger
              className="w-full h-9 bg-surface border border-border rounded-lg text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus"
              aria-label="App Language"
            >
              <Select.Value placeholder="Auto-detect" />
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
                    value="auto"
                    className="text-sm !text-text-primary px-3 py-2 rounded cursor-pointer outline-none focus:bg-surface-hover data-[highlighted]:bg-surface-hover"
                  >
                    <Select.ItemText>Auto-detect</Select.ItemText>
                  </Select.Item>
                  <Select.Separator className="h-px bg-border my-1" />
                  {LANGUAGE_OPTIONS.filter((o) => o.value != null).map((opt) => (
                    <Select.Item
                      key={opt.value!}
                      value={opt.value!}
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
          label="Dictation Language"
          helper="Language to transcribe. Auto-detect is slower but language-agnostic."
          layout="stacked"
        >
          <Select.Root
            value={languageToSelectValue(pendingSettings.dictation_language)}
            onValueChange={(v) =>
              setPendingSettings((s) => ({
                ...s,
                dictation_language: selectValueToLanguage(v),
              }))
            }
          >
            <Select.Trigger
              className="w-full h-9 bg-surface border border-border rounded-lg text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus"
              aria-label="Dictation Language"
            >
              <Select.Value placeholder="Auto-detect" />
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
                    value="auto"
                    className="text-sm !text-text-primary px-3 py-2 rounded cursor-pointer outline-none focus:bg-surface-hover data-[highlighted]:bg-surface-hover"
                  >
                    <Select.ItemText>Auto-detect</Select.ItemText>
                  </Select.Item>
                  <Select.Separator className="h-px bg-border my-1" />
                  {LANGUAGE_OPTIONS.filter((o) => o.value != null).map((opt) => (
                    <Select.Item
                      key={opt.value!}
                      value={opt.value!}
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
      </SettingGroup>

      <SettingGroup title="Appearance">
        <SettingRow
          label="Theme"
          helper="Controls the app color scheme"
          layout="stacked"
        >
          <Select.Root
            value={pendingSettings.theme}
            onValueChange={(v) => handleThemeChange(v as Theme)}
          >
            <Select.Trigger
              className="w-full h-9 bg-surface border border-border rounded-lg text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus"
              aria-label="Theme"
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
                  {THEME_OPTIONS.map((opt) => (
                    <Select.Item
                      key={opt.value}
                      value={opt.value}
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
      </SettingGroup>

      <SettingGroup title="History">
        <SettingRow
          label="Save History"
          helper="Store transcriptions for later review"
          layout="inline"
        >
          <Switch.Root
            checked={pendingSettings.save_history}
            onCheckedChange={(checked) =>
              setPendingSettings((s) => ({ ...s, save_history: checked }))
            }
            className="relative w-10 h-[22px] rounded-full border border-border bg-surface-hover data-[state=checked]:bg-accent data-[state=checked]:border-accent focus:outline-none focus:ring-2 focus:ring-border-focus cursor-pointer"
            aria-label="Save History"
          >
            <Switch.Thumb className="block w-[18px] h-[18px] rounded-full bg-background border border-border translate-x-0.5 data-[state=checked]:translate-x-[18px] transition-transform duration-200" />
          </Switch.Root>
        </SettingRow>

        {saveHistoryOn && (
          <>
            <SettingRow
              label="History Limit"
              helper="Maximum number of transcriptions to keep"
              layout="stacked"
            >
              <Select.Root
                value={
                  pendingSettings.history_limit === "unlimited"
                    ? "unlimited"
                    : String(pendingSettings.history_limit)
                }
                onValueChange={(v) =>
                  setPendingSettings((s) => ({
                    ...s,
                    history_limit: v === "unlimited" ? "unlimited" : (Number(v) as HistoryLimit),
                  }))
                }
              >
                <Select.Trigger
                  className="w-full h-9 bg-surface border border-border rounded-lg text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus"
                  aria-label="History Limit"
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
                      {HISTORY_LIMIT_OPTIONS.map((opt) => (
                        <Select.Item
                          key={String(opt.value)}
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
            {pendingSettings.history_limit === "unlimited" && (
              <p
                className="text-text-muted mt-1"
                style={{ fontSize: "11px" }}
              >
                ℹ With unlimited history, use the History screen to delete items.
              </p>
            )}
          </>
        )}
      </SettingGroup>

    </div>
  );
}
