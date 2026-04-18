/**
 * Read-only input that captures the next keypress when focused.
 * Supports modifier + key (e.g. Ctrl+Space). Rejects Escape, Enter, Tab,
 * and single letter/number without modifier.
 */
import { useCallback, useState } from "react";

interface HotkeyCaptureProps {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  /** When true, omit the internal label (for use inside SettingRow). */
  hideLabel?: boolean;
}

const RESTRICTED_KEYS = new Set(["Escape", "Enter", "Tab"]);

/** Modifier-only keydowns are ignored so user can press e.g. Ctrl then R to get Ctrl+R. */
const MODIFIER_KEYS = new Set(["Control", "Meta", "Alt", "Shift"]);

function formatKey(key: string): string {
  if (key === " ") return "Space";
  if (key.length === 1) return key;
  return key;
}

function isLetterOrNumber(key: string): boolean {
  return /^[a-zA-Z0-9]$/.test(key);
}

/** Build display string from modifiers + key (platform-aware: Cmd on macOS, Ctrl elsewhere). */
function formatHotkey(meta: boolean, ctrl: boolean, shift: boolean, alt: boolean, key: string): string {
  const isMac = typeof navigator !== "undefined" && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
  const parts: string[] = [];
  if (meta) parts.push(isMac ? "Cmd" : "Super");
  if (ctrl) parts.push("Ctrl");
  if (alt) parts.push(isMac ? "Option" : "Alt");
  if (shift) parts.push("Shift");
  parts.push(formatKey(key));
  return parts.join("+");
}

export function HotkeyCapture({ value, onChange, disabled, hideLabel }: HotkeyCaptureProps) {
  const [isListening, setIsListening] = useState(false);
  const [restrictMessage, setRestrictMessage] = useState<string | null>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (disabled) return;
      e.preventDefault();
      e.stopPropagation();

      if (e.repeat) return;
      if (MODIFIER_KEYS.has(e.key)) return;

      if (RESTRICTED_KEYS.has(e.key)) {
        setRestrictMessage("This key cannot be used as the hotkey.");
        return;
      }
      const hasModifier = e.metaKey || e.ctrlKey || e.altKey;
      if (isLetterOrNumber(e.key) && !hasModifier) {
        setRestrictMessage("Use a modifier (Ctrl, Alt, etc.) with letter keys to avoid conflicts.");
        return;
      }
      if (e.key === " " && !hasModifier) {
        setRestrictMessage("Space needs a modifier (e.g. Ctrl+Space) — bare Space conflicts with typing.");
        return;
      }

      const hotkey = formatHotkey(e.metaKey, e.ctrlKey, e.shiftKey, e.altKey, e.key);
      setRestrictMessage(null);
      onChange(hotkey);
      (e.target as HTMLInputElement).blur();
      setIsListening(false);
    },
    [disabled, onChange]
  );

  const handleFocus = useCallback(() => {
    if (disabled) return;
    setIsListening(true);
    setRestrictMessage(null);
  }, [disabled]);

  const handleBlur = useCallback(() => {
    setIsListening(false);
    setRestrictMessage(null);
  }, []);

  const waylandTitle = disabled ? "Hotkey unavailable on Wayland — see warning above" : undefined;

  return (
    <div>
      {!hideLabel && (
        <p className="text-[11px] uppercase tracking-caps text-text-muted font-medium mb-2">
          Push-to-talk hotkey
        </p>
      )}
      <div className="relative">
        <input
          type="text"
          value={isListening ? "" : value}
          readOnly
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={isListening ? "Press a key..." : "Space"}
          title={waylandTitle}
          className={`w-full h-9 bg-surface border rounded-input text-sm font-mono text-text-primary px-3 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-0 focus:ring-offset-background ${
            isListening ? "border-accent" : "border-border"
          } ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
          disabled={disabled}
          aria-label="Push-to-talk hotkey"
        />
        {restrictMessage && (
          <p
            className="text-xs text-warning mt-1.5"
            role="alert"
          >
            {restrictMessage}
          </p>
        )}
      </div>
    </div>
  );
}
