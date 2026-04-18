/**
 * Shared transcriptions state so TranscriptionsSync and HistoryScreen
 * see the same list and updates appear in real time.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Transcription } from "../types";
import {
  generateId,
  getDateGroupLabel,
  loadFromStorage,
  saveToStorage,
} from "../lib/transcriptionStorage";

export interface AddTranscriptionMetadata {
  durationMs?: number | null;
  transcriptionMs?: number | null;
  confidence?: number | null;
  detected_language?: string | null;
}

export interface TranscriptionGroup {
  label: string;
  items: Transcription[];
}

export interface UseTranscriptionsReturn {
  transcriptions: Transcription[];
  groupedTranscriptions: TranscriptionGroup[];
  addTranscription: (text: string, metadata?: AddTranscriptionMetadata) => void;
  deleteTranscription: (id: string) => void;
  clearAll: () => void;
  clearAllTranscriptions: () => Promise<void>;
}

const TranscriptionsContext = createContext<UseTranscriptionsReturn | null>(
  null
);

export function TranscriptionsProvider({ children }: { children: ReactNode }) {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>(() =>
    loadFromStorage()
  );

  const addTranscription = useCallback(
    (text: string, metadata?: AddTranscriptionMetadata) => {
      const t: Transcription = {
        id: generateId(),
        text,
        timestamp: new Date().toISOString(),
        duration_ms: metadata?.durationMs ?? null,
        transcription_ms: metadata?.transcriptionMs ?? null,
        confidence: metadata?.confidence ?? null,
        detected_language: metadata?.detected_language ?? null,
      };
      setTranscriptions((prev) => {
        const next = [t, ...prev];
        saveToStorage(next);
        return next;
      });
    },
    []
  );

  const deleteTranscription = useCallback((id: string) => {
    setTranscriptions((prev) => {
      const next = prev.filter((x) => x.id !== id);
      saveToStorage(next);
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    setTranscriptions([]);
    saveToStorage([]);
  }, []);

  const groupedTranscriptions = useMemo(() => {
    const byLabel = new Map<string, Transcription[]>();
    for (const t of transcriptions) {
      const label = getDateGroupLabel(t.timestamp);
      const list = byLabel.get(label) ?? [];
      list.push(t);
      byLabel.set(label, list);
    }
    const order = ["Today", "Yesterday"];
    const rest = [...byLabel.keys()].filter((k) => !order.includes(k));
    rest.sort((a, b) => {
      const dA = byLabel.get(a)?.[0]?.timestamp ?? "";
      const dB = byLabel.get(b)?.[0]?.timestamp ?? "";
      return dB.localeCompare(dA);
    });
    return [...order.filter((l) => byLabel.has(l)), ...rest].map((label) => ({
      label,
      items: byLabel.get(label) ?? [],
    }));
  }, [transcriptions]);

  const value: UseTranscriptionsReturn = useMemo(
    () => ({
      transcriptions,
      groupedTranscriptions,
      addTranscription,
      deleteTranscription,
      clearAll,
      clearAllTranscriptions: async () => clearAll(),
    }),
    [
      transcriptions,
      groupedTranscriptions,
      addTranscription,
      deleteTranscription,
      clearAll,
    ]
  );

  return (
    <TranscriptionsContext.Provider value={value}>
      {children}
    </TranscriptionsContext.Provider>
  );
}

export function useTranscriptionsContext(): UseTranscriptionsReturn {
  const ctx = useContext(TranscriptionsContext);
  if (ctx == null) {
    throw new Error(
      "useTranscriptionsContext must be used within TranscriptionsProvider"
    );
  }
  return ctx;
}
