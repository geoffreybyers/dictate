/**
 * Read-only path (or any string) with copy-to-clipboard button.
 */
import { useCallback, useState } from "react";
import { Check, Copy } from "lucide-react";

interface PathDisplayProps {
  value: string;
  placeholder?: string;
  /** Optional aria label for the copy button */
  copyLabel?: string;
}

export function PathDisplay({ value, placeholder = "—", copyLabel = "Copy" }: PathDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setCopied(true);
    const t = setTimeout(() => {
      setCopied(false);
    }, 1500);
    return () => clearTimeout(t);
  }, [value]);

  const displayValue = value || placeholder;

  return (
    <div className="flex items-center gap-2 w-full">
      <input
        type="text"
        readOnly
        value={displayValue}
        className="flex-1 h-9 bg-surface border border-border rounded-lg text-sm font-mono text-text-muted px-3 focus:outline-none min-w-0"
        aria-label="Path"
      />
      <button
        type="button"
        onClick={handleCopy}
        disabled={!value}
        className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-border-focus disabled:opacity-50"
        aria-label={copyLabel}
      >
        {copied ? (
          <Check className="w-4 h-4 text-success" aria-hidden />
        ) : (
          <Copy className="w-4 h-4" aria-hidden />
        )}
      </button>
    </div>
  );
}
