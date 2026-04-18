/**
 * dictate — v2 app shell: Header, LeftNav, ContentArea, SaveBar.
 * Active screen state in memory (resets to General on restart).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { getCurrentWindow, currentMonitor } from "@tauri-apps/api/window";
import { LogicalPosition, LogicalSize } from "@tauri-apps/api/dpi";
import { invoke } from "@tauri-apps/api/core";
import { useAppState } from "./hooks/useAppState";
import { useSettings } from "./hooks/useSettings";
import { useTheme } from "./hooks/useTheme";
import { DEFAULT_SETTINGS } from "./types";
import type { Device, NavScreen } from "./types";
import { SettingsProvider } from "./contexts/SettingsContext";
import { TranscriptionsProvider } from "./contexts/TranscriptionsContext";
import { TranscriptionsSync } from "./components/TranscriptionsSync";
import { Header } from "./components/layout/Header";
import { LeftNav } from "./components/layout/LeftNav";
import { ContentArea } from "./components/layout/ContentArea";
import { SaveBar } from "./components/layout/SaveBar";
import { Toast, type ToastTone } from "./components/layout/Toast";
import { GeneralScreen } from "./components/screens/GeneralScreen";
import { ModelScreen } from "./components/screens/ModelScreen";
import { AdvancedScreen } from "./components/screens/AdvancedScreen";
import { HistoryScreen } from "./components/screens/HistoryScreen";

const SETTINGS_SCREENS: NavScreen[] = ["general", "model"];
function isSettingsScreen(screen: NavScreen): boolean {
  return SETTINGS_SCREENS.includes(screen);
}

function renderScreen(
  screen: NavScreen,
  onNavigate?: (s: NavScreen) => void,
  modelDevice?: { value: Device; onChange: (v: Device) => void }
) {
  switch (screen) {
    case "general":
      return <GeneralScreen />;
    case "model":
      return (
        <ModelScreen
          deviceValue={modelDevice!.value}
          onDeviceChange={modelDevice!.onChange}
        />
      );
    case "advanced":
      return <AdvancedScreen />;
    case "history":
      return <HistoryScreen onNavigate={onNavigate} />;
    default:
      return <GeneralScreen />;
  }
}

export default function App() {
  const [activeScreen, setActiveScreen] = useState<NavScreen>("general");
  const [showSavedFeedback, setShowSavedFeedback] = useState(false);
  const [toast, setToast] = useState<{ message: string; tone: ToastTone } | null>(null);
  const savedFeedbackTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Pending device on Model screen; null = use saved. Cleared when navigating away. */
  const [modelPendingDevice, setModelPendingDevice] = useState<Device | null>(null);

  const appState = useAppState();
  const settings = useSettings(DEFAULT_SETTINGS);
  const { savedSettings, isDirty, save, discard, saving, requestStatus } = settings;

  useTheme(savedSettings.theme);

  const modelDeviceDirty =
    activeScreen === "model" &&
    modelPendingDevice != null &&
    modelPendingDevice !== savedSettings.device;
  const [displayResult, setDisplayResult] = useState<{
    text: string;
    durationMs: number;
  } | null>(null);
  const displayResultTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const saveBarVisible =
    (isDirty && isSettingsScreen(activeScreen)) || modelDeviceDirty || showSavedFeedback;

  // Clear model pending device when leaving Model screen
  useEffect(() => {
    if (activeScreen !== "model") setModelPendingDevice(null);
  }, [activeScreen]);

  // Defer first request so sidecar_event listener in useAppState is registered before "ready" arrives
  useEffect(() => {
    const t = setTimeout(() => requestStatus(), 150);
    return () => clearTimeout(t);
  }, [requestStatus]);

  // Show "Copied to clipboard" in header for 3 seconds after each transcription
  useEffect(() => {
    const r = appState.lastResult;
    if (!r) return;
    setDisplayResult({ text: r.text, durationMs: r.durationMs });
    if (displayResultTimeout.current) clearTimeout(displayResultTimeout.current);
    displayResultTimeout.current = setTimeout(() => {
      setDisplayResult(null);
      displayResultTimeout.current = null;
    }, 3000);
    return () => {
      if (displayResultTimeout.current) clearTimeout(displayResultTimeout.current);
    };
  }, [appState.lastResult]);

  // Restore window position/size from settings; center if outside bounds
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const bounds = await invoke<[number, number, number | null, number | null]>(
          "get_saved_window_bounds"
        );
        const [w, h, x, y] = bounds;
        const win = getCurrentWindow();
        if (w > 0 && h > 0) {
          await win.setSize(new LogicalSize(w, h));
        }
        if (x != null && y != null) {
          await win.setPosition(new LogicalPosition(x, y));
          const [pos, size, mon] = await Promise.all([
            win.innerPosition(),
            win.innerSize(),
            currentMonitor(),
          ]);
          if (mon?.workArea) {
            const wa = mon.workArea;
            if (
              pos.x < wa.position.x ||
              pos.y < wa.position.y ||
              pos.x + size.width > wa.position.x + wa.size.width ||
              pos.y + size.height > wa.position.y + wa.size.height
            ) {
              await win.center();
            }
          }
        } else {
          await win.center();
        }
      } catch {
        if (!cancelled) {
          getCurrentWindow().center().catch(() => {});
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist window position/size on resize or move (debounced)
  const saveWindowBounds = useCallback(() => {
    const win = getCurrentWindow();
    Promise.all([win.innerSize(), win.innerPosition(), win.scaleFactor()])
      .then(([size, position, scale]) => {
        const logicalW = Math.round(size.width / scale);
        const logicalH = Math.round(size.height / scale);
        const logicalX = Math.round(position.x / scale);
        const logicalY = Math.round(position.y / scale);
        save({
          ...savedSettings,
          window_width: logicalW,
          window_height: logicalH,
          window_x: logicalX,
          window_y: logicalY,
        });
      })
      .catch(() => {});
  }, [save, savedSettings]);

  useEffect(() => {
    const win = getCurrentWindow();
    let timeout: ReturnType<typeof setTimeout> | null = null;
    const scheduleSave = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        timeout = null;
        saveWindowBounds();
      }, 500);
    };
    const unlistenResized = win.onResized(() => scheduleSave());
    const unlistenMoved = win.onMoved(() => scheduleSave());
    return () => {
      unlistenResized.then((fn) => fn());
      unlistenMoved.then((fn) => fn());
      if (timeout) clearTimeout(timeout);
    };
  }, [saveWindowBounds]);

  const handleSave = async () => {
    try {
      if (modelDeviceDirty) {
        await save({ ...savedSettings, device: modelPendingDevice! });
        setModelPendingDevice(null);
        try {
          await invoke("restart_sidecar");
        } catch {
          // ignore
        }
      } else {
        await save();
      }
      setShowSavedFeedback(true);
      if (savedFeedbackTimeout.current) clearTimeout(savedFeedbackTimeout.current);
      savedFeedbackTimeout.current = setTimeout(() => {
        setShowSavedFeedback(false);
        savedFeedbackTimeout.current = null;
      }, 1500);
    } catch (e) {
      // Save failed — most likely the hotkey couldn't be bound (portal
      // denial on Wayland, conflicting accelerator on X11, etc.). Show
      // the error in a toast so the user can act on it.
      const message = e instanceof Error ? e.message : String(e);
      setToast({ message, tone: "error" });
    }
  };

  const handleDiscard = () => {
    if (modelDeviceDirty) {
      setModelPendingDevice(null);
    } else {
      discard();
    }
  };

  return (
    <SettingsProvider value={settings}>
      <TranscriptionsProvider>
        <TranscriptionsSync />
        <div className="h-screen flex flex-col bg-background text-text-primary font-sans overflow-hidden">
        <Header />
      <div className="flex flex-1 min-h-0">
        <LeftNav
          activeScreen={activeScreen}
          onSelect={setActiveScreen}
          hotkey={savedSettings.hotkey}
          lastResult={displayResult}
        />
        <div className="flex-1 flex flex-col min-h-0 relative">
          <ContentArea>
            {renderScreen(activeScreen, setActiveScreen, {
              value: modelPendingDevice ?? savedSettings.device,
              onChange: setModelPendingDevice,
            })}
          </ContentArea>
          <div className="absolute bottom-0 left-0 right-0 overflow-hidden">
            <SaveBar
              visible={saveBarVisible}
              onDiscard={handleDiscard}
              onSave={handleSave}
              saving={saving}
              saved={showSavedFeedback}
            />
          </div>
        </div>
      </div>
    </div>
    <Toast
      message={toast?.message ?? null}
      tone={toast?.tone}
      onDismiss={() => setToast(null)}
    />
      </TranscriptionsProvider>
    </SettingsProvider>
  );
}
