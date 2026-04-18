/**
 * Status bar: loading / ready / recording / transcribing / last result / error.
 */
import type { AppState } from "../types";

interface StatusBarProps {
  status: AppState;
  queueDepth: number;
  hotkey: string;
  error: { code: string; message?: string } | null;
  lastResult: { text: string; durationMs: number } | null;
}

export function StatusBar({
  status,
  queueDepth,
  hotkey,
  error,
  lastResult,
}: StatusBarProps) {
  return (
    <div
      className="h-12 px-panel flex items-center bg-surface transition-opacity duration-200 ease-in-out"
      role="status"
      aria-live="polite"
      aria-label={
        error
          ? "Error"
          : status === "loading"
            ? "Loading model"
            : status === "recording"
              ? "Recording"
              : status === "transcribing"
                ? "Transcribing"
                : lastResult
                  ? "Result copied"
                  : "Ready"
      }
    >
      {error && (
        <span className="text-sm text-error">⚠ {error.message ?? error.code}</span>
      )}
      {!error && status === "loading" && (
        <div className="flex items-center gap-2 w-full">
          <span className="text-sm text-text-secondary">
            Loading model... (this may take a moment)
          </span>
          <span className="status-bar-shimmer flex-1 min-w-[60px] h-2 rounded bg-surface-hover overflow-hidden" />
        </div>
      )}
      {!error && status === "recording" && (
        <>
          <span
            className="inline-block w-3 h-3 rounded-full bg-recording mr-2 animate-pulse-dot"
            aria-hidden
          />
          <span className="text-sm text-text-primary">● Recording...</span>
        </>
      )}
      {!error && status === "transcribing" && (
        <div className="flex items-center justify-between w-full">
          <span className="text-sm text-warning">⏳ Transcribing...</span>
          {queueDepth > 0 && (
            <span className="text-xs text-text-muted">{queueDepth} queued</span>
          )}
        </div>
      )}
      {!error && !status.match(/recording|transcribing|loading/) && lastResult && (
        <span className="text-sm text-success">
          ✓ Copied to clipboard · {(lastResult.durationMs / 1000).toFixed(1)}s
        </span>
      )}
      {!error &&
        !status.match(/recording|transcribing|loading/) &&
        !lastResult &&
        status !== "loading" && (
          <span className="text-sm text-text-secondary">
            Hold{" "}
            <kbd className="bg-surface-hover border border-border rounded-md px-1.5 py-0.5 font-mono text-xs">
              {hotkey}
            </kbd>{" "}
            to transcribe
          </span>
        )}
    </div>
  );
}
