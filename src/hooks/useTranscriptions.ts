/**
 * Transcription history: list, add, delete, clear.
 * State lives in TranscriptionsContext; this hook exposes it for backward compatibility.
 */
export {
  useTranscriptionsContext as useTranscriptions,
  type AddTranscriptionMetadata,
  type TranscriptionGroup,
  type UseTranscriptionsReturn,
} from "../contexts/TranscriptionsContext";
