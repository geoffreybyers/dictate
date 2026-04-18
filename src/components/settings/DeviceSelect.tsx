import type { Device } from "../../types";

interface DeviceSelectProps {
  value: Device;
  cudaAvailable: boolean;
  onChange: (v: Device) => void;
}

export function DeviceSelect({ value, cudaAvailable, onChange }: DeviceSelectProps) {
  const showCudaWarning = value === "cuda" && !cudaAvailable;
  return (
    <div
      role="group"
      aria-label="Compute device"
    >
      <p className="text-[11px] uppercase tracking-caps text-text-muted font-medium mb-2" id="device-label">
        Device
      </p>
      <div className="flex gap-1 p-0.5 bg-surface border border-border rounded-input h-9">
        <button
          type="button"
          role="radio"
          aria-checked={value === "cpu"}
          aria-label="CPU"
          onClick={() => onChange("cpu")}
          className={`flex-1 rounded-[6px] text-sm font-medium transition-all duration-150 ${
            value === "cpu" ? "bg-accent text-on-accent" : "text-text-secondary hover:text-text-primary"
          }`}
        >
          CPU
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={value === "cuda"}
          aria-label="CUDA"
          onClick={() => onChange("cuda")}
          className={`flex-1 rounded-[6px] text-sm font-medium transition-all duration-150 ${
            value === "cuda" ? "bg-accent text-on-accent" : "text-text-secondary hover:text-text-primary"
          }`}
        >
          CUDA
        </button>
      </div>
      {showCudaWarning && (
        <p className="text-xs text-warning mt-1.5">
          ⚠ GPU not available — transcription is using CPU. CTranslate2 (used by this app) did not detect CUDA; you may need a CUDA 12.x–compatible build or check the terminal for &quot;supported devices&quot;.
        </p>
      )}
      {!showCudaWarning && (
        <p className="text-xs text-text-muted mt-1.5">
          {value === "cpu" ? "Works on all hardware" : "Requires NVIDIA GPU with CUDA drivers"}
        </p>
      )}
    </div>
  );
}
