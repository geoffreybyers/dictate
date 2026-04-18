/**
 * Transcription list persistence and grouping helpers. Shared by TranscriptionsContext.
 */
import type { Transcription } from "../types";

export const STORAGE_KEY = "dictate_transcriptions";

export function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export function loadFromStorage(): Transcription[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    const list = parsed.filter(
      (t): t is Record<string, unknown> =>
        t != null &&
        typeof t === "object" &&
        typeof (t as Record<string, unknown>).id === "string" &&
        typeof (t as Record<string, unknown>).text === "string" &&
        typeof (t as Record<string, unknown>).timestamp === "string"
    );
    return list.map((t) => ({
      ...t,
      duration_ms: t.duration_ms ?? null,
      transcription_ms: t.transcription_ms ?? null,
      confidence: t.confidence ?? null,
      detected_language: t.detected_language ?? null,
    })) as Transcription[];
  } catch {
    return [];
  }
}

export function saveToStorage(items: Transcription[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // ignore quota or other storage errors
  }
}

/** Format date group label: "Today", "Yesterday", or "Month DD, YYYY" */
export function getDateGroupLabel(isoDate: string): string {
  const d = new Date(isoDate);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const itemDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());

  if (itemDay.getTime() === today.getTime()) return "Today";
  if (itemDay.getTime() === yesterday.getTime()) return "Yesterday";
  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}
