interface AutoPasteToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
}

export function AutoPasteToggle({ value, onChange }: AutoPasteToggleProps) {
  return (
    <div className="flex items-center justify-between gap-4 min-h-[44px]">
      <div>
        <p className="text-base text-text-primary font-medium">Auto-paste</p>
        <p className="text-xs text-text-muted mt-0.5">
          After transcription, simulate Paste so text appears in the focused app. May not work on
          Wayland; on macOS, Input Monitoring may be required.
        </p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`relative w-10 h-[22px] rounded-full border flex-shrink-0 transition-colors duration-200 ${
          value ? "bg-accent border-accent" : "bg-surface-hover border-border"
        }`}
      >
        <span
          className={`absolute top-[2px] w-[18px] h-[18px] rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.4)] transition-transform duration-200 ${
            value ? "left-[20px]" : "left-[2px]"
          }`}
        />
      </button>
    </div>
  );
}
