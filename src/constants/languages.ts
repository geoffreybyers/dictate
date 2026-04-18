import type { Language } from "../types";

/** Auto-detect, then all supported languages. */
export const LANGUAGE_OPTIONS: { value: Language; label: string }[] = [
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

export function languageToSelectValue(lang: Language): string {
  return lang == null ? "auto" : lang;
}

export function selectValueToLanguage(v: string): Language {
  return v === "auto" ? null : (v as Language);
}
