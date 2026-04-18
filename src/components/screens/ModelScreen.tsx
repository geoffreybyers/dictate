/**
 * Model screen: Hardware (Device/CUDA/Microphone), Model (Size/Compute/Cache), Silence.
 */
import { useCallback, useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Select from "@radix-ui/react-select";
import * as Switch from "@radix-ui/react-switch";
import { ChevronDown, RefreshCw } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { useSettingsContext } from "../../contexts/SettingsContext";
import { useAppState } from "../../hooks/useAppState";
import type { ComputeType, Device, ModelSize } from "../../types";
import { PathDisplay } from "../settings/PathDisplay";
import { SettingGroup } from "../settings/SettingGroup";
import { SettingRow } from "../settings/SettingRow";
import { WaylandBanner } from "../WaylandBanner";

const MODEL_SIZE_OPTIONS: { value: ModelSize; label: string }[] = [
  { value: "small", label: "Small (~500MB RAM, fast)" },
  { value: "medium", label: "Medium (~1.3GB RAM, more accurate)" },
];

const COMPUTE_TYPE_OPTIONS: { value: ComputeType; label: string }[] = [
  { value: "auto", label: "Auto (recommended)" },
  { value: "int8", label: "int8" },
  { value: "float16", label: "float16" },
  { value: "int8_float16", label: "int8_float16" },
];

const DEVICE_OPTIONS: { value: Device; label: string }[] = [
  { value: "cpu", label: "CPU" },
  { value: "cuda", label: "CUDA (NVIDIA GPU)" },
];

/** Sentinel value for "System Default" microphone; Radix Select forbids empty string as Select.Item value. */
const INPUT_DEVICE_SYSTEM_DEFAULT = "__system_default__";

const INVOKE_TIMEOUT_MS = 5000;

function invokeWithTimeout<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return Promise.race([
    args != null ? invoke<T>(cmd, args) : invoke<T>(cmd),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("timeout")), INVOKE_TIMEOUT_MS)
    ),
  ]);
}

/** Compute type is incompatible with CPU when it requires GPU (float16 variants). */
function isComputeIncompatibleWithDevice(compute: ComputeType, device: Device): boolean {
  if (device === "cuda") return false;
  return compute === "float16" || compute === "int8_float16";
}

export interface ModelScreenProps {
  /** Current device (saved or pending). Save bar in App when pending !== saved. */
  deviceValue: Device;
  /** Called when user changes Device select; sets pending device in App. */
  onDeviceChange: (device: Device) => void;
}

export function ModelScreen({ deviceValue, onDeviceChange }: ModelScreenProps) {
  const { savedSettings, pendingSettings, setPendingSettings, save, getConfigPath, requestStatus } =
    useSettingsContext();
  const appState = useAppState();
  const [modelSizeDialogOpen, setModelSizeDialogOpen] = useState(false);
  const [pendingModelSize, setPendingModelSize] = useState<ModelSize | null>(null);
  const [modelCachePath, setModelCachePath] = useState<string>("");
  const [inputDevices, setInputDevices] = useState<{ id: string; label: string }[]>([
    { id: INPUT_DEVICE_SYSTEM_DEFAULT, label: "System Default" },
  ]);

  useEffect(() => {
    requestStatus();
  }, [requestStatus]);

  useEffect(() => {
    getConfigPath().then((p) => {
      if (p) setModelCachePath(p);
    });
  }, [getConfigPath]);

  const refreshInputDevices = useCallback(async () => {
    try {
      const raw = await invokeWithTimeout<unknown>("get_input_devices");
      const list = Array.isArray(raw)
        ? raw.map((d: unknown) =>
            d && typeof d === "object" && "id" in d && "label" in d
              ? { id: String((d as { id: string }).id), label: String((d as { label: string }).label) }
              : typeof d === "string"
                ? { id: d, label: d }
                : { id: "", label: "—" }
          )
        : [];
      setInputDevices([{ id: INPUT_DEVICE_SYSTEM_DEFAULT, label: "System Default" }, ...list]);
    } catch {
      setInputDevices([{ id: INPUT_DEVICE_SYSTEM_DEFAULT, label: "System Default" }]);
    }
  }, []);

  useEffect(() => {
    refreshInputDevices();
  }, [refreshInputDevices]);

  const handleModelSizeChange = (newSize: ModelSize) => {
    if (newSize === savedSettings.model_size) return;
    setPendingModelSize(newSize);
    setModelSizeDialogOpen(true);
  };

  const confirmModelSizeChange = useCallback(async () => {
    if (pendingModelSize == null) return;
    await save({ ...savedSettings, model_size: pendingModelSize });
    setModelSizeDialogOpen(false);
    setPendingModelSize(null);
  }, [pendingModelSize, savedSettings, save]);

  const computeIncompatible = isComputeIncompatibleWithDevice(
    savedSettings.compute_type,
    savedSettings.device
  );

  return (
    <div className="flex flex-col gap-8" style={{ gap: "32px" }}>
      {appState.sessionType === "wayland" && <WaylandBanner />}

      <SettingGroup title="Hardware">
        <SettingRow label="Device" layout="stacked">
          <Select.Root
            value={deviceValue}
            onValueChange={(v) => onDeviceChange(v as Device)}
          >
            <Select.Trigger className="inline-flex items-center justify-between gap-2 h-9 min-w-[180px] px-3 rounded-lg border border-border bg-surface text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus">
              <Select.Value />
              <Select.Icon className="text-text-muted">
                <ChevronDown className="w-4 h-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 text-text-primary">
                <Select.Viewport className="p-1">
                  {DEVICE_OPTIONS.map((opt) => (
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
        {deviceValue === "cuda" && !appState.cudaAvailable && (
          <p className="text-xs text-warning mt-1">⚠ CUDA not detected — falling back to CPU</p>
        )}

        <SettingRow label="CUDA Version" layout="inline">
          <span className="text-sm font-mono text-text-muted">
            {appState.cudaAvailable && appState.cudaVersion
              ? appState.cudaVersion
              : "Not available"}
          </span>
        </SettingRow>

        <SettingRow label="Microphone" layout="stacked">
          <div className="flex items-center gap-2">
            <Select.Root
              value={savedSettings.input_device ?? INPUT_DEVICE_SYSTEM_DEFAULT}
              onValueChange={(v) =>
                save({
                  ...savedSettings,
                  input_device: v === INPUT_DEVICE_SYSTEM_DEFAULT ? null : v,
                })
              }
            >
              <Select.Trigger className="inline-flex items-center justify-between gap-2 h-9 flex-1 min-w-0 px-3 rounded-lg border border-border bg-surface text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus">
                <Select.Value placeholder="System Default" />
                <Select.Icon className="text-text-muted shrink-0">
                  <ChevronDown className="w-4 h-4" />
                </Select.Icon>
              </Select.Trigger>
              <Select.Portal>
                <Select.Content className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 text-text-primary">
                  <Select.Viewport className="p-1">
                    {inputDevices.map((d) => (
                      <Select.Item
                        key={d.id}
                        value={d.id}
                        className="text-sm !text-text-primary px-2 py-1.5 rounded-md outline-none data-[highlighted]:bg-surface-hover data-[state=checked]:bg-accent/10"
                      >
                        <Select.ItemText>{d.label || "System Default"}</Select.ItemText>
                      </Select.Item>
                    ))}
                  </Select.Viewport>
                </Select.Content>
              </Select.Portal>
            </Select.Root>
            <button
              type="button"
              onClick={refreshInputDevices}
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover"
              aria-label="Refresh microphone list"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </SettingRow>
      </SettingGroup>

      <SettingGroup title="Model">
        <SettingRow label="Model Size" layout="stacked">
          <Select.Root
            value={savedSettings.model_size}
            onValueChange={(v) => handleModelSizeChange(v as ModelSize)}
          >
            <Select.Trigger className="inline-flex items-center justify-between gap-2 h-9 min-w-[180px] px-3 rounded-lg border border-border bg-surface text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus">
              <Select.Value />
              <Select.Icon className="text-text-muted">
                <ChevronDown className="w-4 h-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 text-text-primary">
                <Select.Viewport className="p-1">
                  {MODEL_SIZE_OPTIONS.map((opt) => (
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

        <Dialog.Root open={modelSizeDialogOpen} onOpenChange={setModelSizeDialogOpen}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
            <Dialog.Content
              className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm bg-surface border border-border rounded-lg shadow-lg p-4 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
              onPointerDownOutside={() => setModelSizeDialogOpen(false)}
            >
              <Dialog.Title className="text-base font-semibold text-text-primary">
                Change model size
              </Dialog.Title>
              <Dialog.Description className="text-sm text-text-secondary mt-2">
                Changing model size requires reloading. This will take a few seconds.
              </Dialog.Description>
              <div className="flex justify-end gap-2 mt-4">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover border border-border"
                  >
                    Cancel
                  </button>
                </Dialog.Close>
                <button
                  type="button"
                  onClick={() => {
                    confirmModelSizeChange();
                  }}
                  className="h-8 px-4 rounded-lg text-sm font-medium bg-accent text-on-accent hover:opacity-90"
                >
                  OK
                </button>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>

        <SettingRow
          label="Compute Type"
          helper="Override automatic compute type selection"
          layout="stacked"
        >
          <Select.Root
            value={savedSettings.compute_type}
            onValueChange={(v) => save({ ...savedSettings, compute_type: v as ComputeType })}
          >
            <Select.Trigger className="inline-flex items-center justify-between gap-2 h-9 min-w-[180px] px-3 rounded-lg border border-border bg-surface text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus">
              <Select.Value />
              <Select.Icon className="text-text-muted">
                <ChevronDown className="w-4 h-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50 text-text-primary">
                <Select.Viewport className="p-1">
                  {COMPUTE_TYPE_OPTIONS.map((opt) => (
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
        {computeIncompatible && (
          <p className="text-xs text-warning mt-1">
            Selected compute type may not work well with CPU. Consider using Auto or int8.
          </p>
        )}

        <SettingRow label="Model Cache Directory" layout="stacked">
          <PathDisplay value={modelCachePath} placeholder="—" copyLabel="Copy path" />
        </SettingRow>
      </SettingGroup>

      <SettingGroup title="Silence">
        <SettingRow
          label="VAD Filter"
          helper="Strip silence from recordings before transcription"
          layout="inline"
        >
          <Switch.Root
            checked={pendingSettings.vad_filter}
            onCheckedChange={(checked) =>
              setPendingSettings((s) => ({ ...s, vad_filter: checked }))
            }
            className="relative w-10 h-[22px] rounded-full border border-border bg-surface-hover data-[state=checked]:bg-accent data-[state=checked]:border-accent focus:outline-none focus:ring-2 focus:ring-border-focus cursor-pointer"
            aria-label="VAD Filter"
          >
            <Switch.Thumb className="block w-[18px] h-[18px] rounded-full bg-background border border-border translate-x-0.5 data-[state=checked]:translate-x-[18px] transition-transform duration-200" />
          </Switch.Root>
        </SettingRow>
      </SettingGroup>
    </div>
  );
}
