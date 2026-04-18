import type { ModelSize } from "../../types";

interface ModelSelectProps {
  value: ModelSize;
  onChange: (v: ModelSize) => void;
}

const MODELS: { id: ModelSize; label: string }[] = [
  { id: "small", label: "Small" },
  { id: "medium", label: "Medium" },
];

export function ModelSelect({ value, onChange }: ModelSelectProps) {
  return (
    <div
      role="group"
      aria-label="Model size"
    >
      <p className="text-[11px] uppercase tracking-caps text-text-muted font-medium mb-2" id="model-label">
        Model
      </p>
      <div className="flex gap-1 p-0.5 bg-surface border border-border rounded-input h-9">
        {MODELS.map((m) => (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={value === m.id}
            aria-label={m.label}
            onClick={() => onChange(m.id)}
            className={`flex-1 rounded-[6px] text-sm font-medium transition-all duration-150 ${
              value === m.id
                ? "bg-accent text-on-accent"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-text-muted mt-1.5">
        {value === "small" ? "~500MB RAM · fast" : "~1.3GB RAM · more accurate"}
      </p>
    </div>
  );
}
