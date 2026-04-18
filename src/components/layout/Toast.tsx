/**
 * Lightweight toast notification.
 *
 * Controlled component: parent owns the message + tone. When `message`
 * is non-null the toast slides up from the bottom; clicking × or waiting
 * `durationMs` (default 6s) calls onDismiss.
 *
 * Tones:
 *   "error"    — red border, red text. Use for failures (hotkey bind,
 *                save rejection, sidecar unreachable).
 *   "info"     — neutral. Use for passive notices.
 *   "success"  — green. Use sparingly; the SaveBar's "Saved ✓" already
 *                handles the common success case.
 */
import { useEffect } from "react";

export type ToastTone = "error" | "info" | "success";

interface ToastProps {
  message: string | null;
  tone?: ToastTone;
  durationMs?: number;
  onDismiss: () => void;
}

const TONE_CLASSES: Record<ToastTone, string> = {
  error: "border-error/40 bg-error/[0.08] text-error",
  info: "border-border bg-surface text-text-primary",
  success: "border-success/40 bg-success/[0.08] text-success",
};

const TONE_ICON: Record<ToastTone, string> = {
  error: "⚠",
  info: "ℹ",
  success: "✓",
};

export function Toast({ message, tone = "info", durationMs = 6000, onDismiss }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const id = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(id);
  }, [message, durationMs, onDismiss]);

  const visible = message !== null;

  return (
    <div
      className="pointer-events-none fixed bottom-6 left-1/2 z-50 -translate-x-1/2 transition-all duration-200 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: `translate(-50%, ${visible ? "0" : "12px"})`,
      }}
      aria-live="polite"
      aria-atomic="true"
    >
      {visible && (
        <div
          role="alert"
          className={`pointer-events-auto flex max-w-[560px] items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${TONE_CLASSES[tone]}`}
        >
          <span aria-hidden className="flex-shrink-0 text-base leading-5">
            {TONE_ICON[tone]}
          </span>
          <p className="flex-1 text-sm leading-5 break-words">{message}</p>
          <button
            type="button"
            onClick={onDismiss}
            className="flex-shrink-0 text-text-muted hover:text-text-primary"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
