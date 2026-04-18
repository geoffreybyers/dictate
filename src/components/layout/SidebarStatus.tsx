/**
 * Status text for the sidebar footer: Hold hotkey to transcribe, Recording…, Transcribing…, Copied…, or error.
 * Includes the same colored status dot as the header (green / red / yellow / gray).
 */
import { useAppState } from "../../hooks/useAppState";
import type { AppState as AppStateStatus } from "../../types";

interface SidebarStatusProps {
  hotkey: string;
  lastResult: { text: string; durationMs: number } | null;
}

/** Same dot logic as Header: recording=red, transcribing=yellow, error=red, loading=gray, else=green */
function getStatusDotClass(status: AppStateStatus): string {
  if (status === "recording") return "bg-recording animate-pulse-dot";
  if (status === "transcribing") return "bg-warning animate-pulse-dot";
  if (status === "error") return "bg-error";
  if (status === "loading") return "bg-text-muted";
  return "bg-success";
}

function getStatusText(
  status: AppStateStatus,
  hotkey: string,
  queueDepth: number,
  error: { code: string; message?: string } | null,
  lastResult: { text: string; durationMs: number } | null
) {
  if (error) {
    return (
      <span className="text-sm text-error">⚠ {error.message ?? error.code}</span>
    );
  }
  if (status === "loading") {
    return <span className="text-sm text-text-secondary">Loading model...</span>;
  }
  if (status === "recording") {
    return <span className="text-sm text-recording">Recording...</span>;
  }
  if (status === "transcribing") {
    return (
      <span className="text-sm text-text-secondary">
        Transcribing...
        {queueDepth > 0 && (
          <span className="text-text-muted"> · {queueDepth} queued</span>
        )}
      </span>
    );
  }
  if (lastResult) {
    return (
      <span className="text-sm text-success">
        ✓ Copied to clipboard · {(lastResult.durationMs / 1000).toFixed(1)}s
      </span>
    );
  }
  return (
    <span className="text-sm text-text-secondary">
      Hold{" "}
      <kbd className="font-mono text-xs px-1.5 py-0.5 rounded bg-surface-hover border border-border">
        {hotkey}
      </kbd>{" "}
      to transcribe
    </span>
  );
}

export function SidebarStatus({ hotkey, lastResult }: SidebarStatusProps) {
  const appState = useAppState();
  const statusDotClass = getStatusDotClass(appState.status);
  return (
    <div className="border-t border-border pt-3 px-3 pb-3 flex-shrink-0 flex items-center gap-2">
      <span
        className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusDotClass}`}
        style={{ width: "10px", height: "10px" }}
        aria-hidden
      />
      {getStatusText(
        appState.status,
        hotkey,
        appState.queueDepth,
        appState.error,
        lastResult
      )}
    </div>
  );
}
