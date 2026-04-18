import type { Language } from "../../types";
import * as Select from "@radix-ui/react-select";

const LANGUAGES: { value: Language; label: string }[] = [
  { value: null, label: "Auto-detect" },
  { value: "en", label: "English (en)" },
  { value: "es", label: "Spanish (es)" },
  { value: "fr", label: "French (fr)" },
  { value: "de", label: "German (de)" },
  { value: "it", label: "Italian (it)" },
  { value: "pt", label: "Portuguese (pt)" },
  { value: "nl", label: "Dutch (nl)" },
  { value: "ru", label: "Russian (ru)" },
  { value: "zh", label: "Chinese (zh)" },
  { value: "ja", label: "Japanese (ja)" },
  { value: "ko", label: "Korean (ko)" },
  { value: "ar", label: "Arabic (ar)" },
  { value: "hi", label: "Hindi (hi)" },
];

/** Radix Select uses string value; we use "auto" for null (Auto-detect). */
function toSelectValue(lang: Language): string {
  return lang ?? "auto";
}

function fromSelectValue(v: string): Language {
  return v === "auto" ? null : (v as Language);
}

interface LanguageSelectProps {
  value: Language;
  onChange: (v: Language) => void;
}

export function LanguageSelect({ value, onChange }: LanguageSelectProps) {
  const selectValue = toSelectValue(value);
  return (
    <div>
      <p className="text-[11px] uppercase tracking-caps text-text-muted font-medium mb-2">
        Language
      </p>
      <Select.Root value={selectValue} onValueChange={(v) => onChange(fromSelectValue(v))}>
        <Select.Trigger
          className="w-full h-9 bg-surface border border-border rounded-input text-sm text-text-primary px-3 flex items-center justify-between gap-2 focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus data-[placeholder]:text-text-secondary"
          aria-label="Language"
        >
          <Select.Value placeholder="English (en)" />
          <Select.Icon className="text-text-muted">
            <span aria-hidden>▾</span>
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content
            className="bg-surface border border-border rounded-input shadow-lg overflow-hidden z-50 min-w-[var(--radix-select-trigger-width)] text-text-primary"
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
              {LANGUAGES.filter((l) => l.value !== null).map((l) => (
                <Select.Item
                  key={l.value}
                  value={l.value!}
                  className="text-sm !text-text-primary px-3 py-2 rounded cursor-pointer outline-none focus:bg-surface-hover data-[highlighted]:bg-surface-hover"
                >
                  <Select.ItemText>{l.label}</Select.ItemText>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </div>
  );
}
