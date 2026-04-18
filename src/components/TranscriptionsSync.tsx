/**
 * Always-mounted component that syncs sidecar transcription_complete (appState.lastResult)
 * into the transcription history when save_history is enabled. Keeps the list updated
 * regardless of which screen is visible.
 */
import { useEffect, useRef } from "react";
import { useSettingsContext } from "../contexts/SettingsContext";
import { useAppState } from "../hooks/useAppState";
import { useTranscriptions } from "../hooks/useTranscriptions";

export function TranscriptionsSync() {
  const { savedSettings } = useSettingsContext();
  const appState = useAppState();
  const { addTranscription } = useTranscriptions();
  const lastAddedRef = useRef<{
    text: string;
    durationMs: number;
    transcriptionMs?: number | null;
    confidence?: number | null;
    detected_language?: string | null;
  } | null>(null);

  const saveHistory = savedSettings.save_history;

  useEffect(() => {
    const r = appState.lastResult;
    if (!r || !saveHistory) return;
    if (
      lastAddedRef.current?.text === r.text &&
      lastAddedRef.current?.durationMs === r.durationMs
    ) {
      return;
    }
    lastAddedRef.current = {
      text: r.text,
      durationMs: r.durationMs,
      transcriptionMs: r.transcriptionMs,
      confidence: r.confidence,
      detected_language: r.detected_language,
    };
    addTranscription(r.text, {
      durationMs: r.durationMs,
      transcriptionMs: r.transcriptionMs ?? null,
      confidence: r.confidence ?? null,
      detected_language: r.detected_language ?? null,
    });
  }, [appState.lastResult, saveHistory, addTranscription]);

  return null;
}
