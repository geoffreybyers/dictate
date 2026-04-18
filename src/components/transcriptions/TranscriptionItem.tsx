/**
 * Single transcription card: timestamp, copy/delete, body, optional metadata row.
 * Metadata only shown when the corresponding Advanced toggles are on.
 */
import { useCallback, useState } from "react";
import { Check, Copy, Trash2 } from "lucide-react";
import { useSettingsContext } from "../../contexts/SettingsContext";
import type { Transcription } from "../../types";

interface TranscriptionItemProps {
  item: Transcription;
  onDelete: (id: string) => void;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function TranscriptionItem({ item, onDelete }: TranscriptionItemProps) {
  const { savedSettings } = useSettingsContext();
  const [copied, setCopied] = useState(false);

  const showConfidence = savedSettings.show_confidence && item.confidence != null;
  const showAudio = savedSettings.show_timing && item.duration_ms != null;
  const showTranscribe = savedSettings.show_timing && item.transcription_ms != null;
  const showTiming = showAudio || showTranscribe;
  const showLanguage = savedSettings.show_detected_language && item.detected_language != null;
  const showMetadata = showConfidence || showTiming || showLanguage;

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(item.text);
    setCopied(true);
    const t = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(t);
  }, [item.text]);

  return (
    <div
      className="bg-surface border border-border rounded-[10px] p-[14px_16px] mb-2"
      style={{ padding: "14px 16px" }}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-text-muted text-[11px]">{formatTime(item.timestamp)}</span>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={handleCopy}
            className="w-7 h-7 flex items-center justify-center rounded text-text-muted hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus"
            aria-label="Copy"
          >
            {copied ? (
              <Check className="w-4 h-4 text-success" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button
            type="button"
            onClick={() => onDelete(item.id)}
            className="w-7 h-7 flex items-center justify-center rounded text-text-muted hover:text-error focus:outline-none focus:ring-2 focus:ring-border-focus"
            aria-label="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div
        className="text-text-primary select-text leading-[1.6]"
        style={{ fontSize: "13px", fontWeight: 400 }}
      >
        {item.text}
      </div>
      {showMetadata && (
        <div
          className="border-t border-border mt-2 pt-2 text-text-muted text-[11px] font-mono"
          style={{ borderTopWidth: "1px", marginTop: "8px", paddingTop: "8px" }}
        >
          {showConfidence && (
            <span>Confidence: {Math.round((item.confidence ?? 0) * 100)}%</span>
          )}
          {showConfidence && showTiming && " · "}
          {showAudio && (
            <span>{(item.duration_ms! / 1000).toFixed(3)}s audio</span>
          )}
          {showAudio && showTranscribe && " · "}
          {showTranscribe && (
            <span>
              {item.transcription_ms! >= 1000
                ? `${(item.transcription_ms! / 1000).toFixed(1)}s transcribe`
                : `${item.transcription_ms}ms transcribe`}
            </span>
          )}
          {(showConfidence || showTiming) && showLanguage && " · "}
          {showLanguage && <span>{item.detected_language}</span>}
        </div>
      )}
    </div>
  );
}
