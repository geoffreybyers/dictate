/**
 * History screen: list transcriptions by date, clear all, empty/history-disabled states.
 * Adding new transcriptions to the list is handled by TranscriptionsSync (always mounted).
 */
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { History, Mic } from "lucide-react";
import { useSettingsContext } from "../../contexts/SettingsContext";
import { useTranscriptions } from "../../hooks/useTranscriptions";
import type { NavScreen } from "../../types";
import { TranscriptionItem } from "../transcriptions/TranscriptionItem";

interface HistoryScreenProps {
  onNavigate?: (screen: NavScreen) => void;
}

export function HistoryScreen({ onNavigate }: HistoryScreenProps) {
  const { savedSettings } = useSettingsContext();
  const {
    transcriptions,
    groupedTranscriptions,
    deleteTranscription,
    clearAll,
  } = useTranscriptions();
  const [clearDialogOpen, setClearDialogOpen] = useState(false);

  const saveHistory = savedSettings.save_history;
  const hotkey = savedSettings.hotkey;

  const handleClearAll = () => {
    clearAll();
    setClearDialogOpen(false);
  };

  if (!saveHistory) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between gap-4 mb-6">
          <h1
            className="text-text-primary font-semibold"
            style={{ fontSize: "15px", fontWeight: 600 }}
          >
            History
          </h1>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center min-h-[200px]">
          <History className="w-8 h-8 text-text-muted mb-3" aria-hidden />
          <p className="text-text-muted font-medium" style={{ fontWeight: 500 }}>
            History is disabled
          </p>
          <p className="text-text-muted text-sm mt-1 text-center max-w-sm">
            Enable Save History in{" "}
            {onNavigate ? (
              <button
                type="button"
                onClick={() => onNavigate("general")}
                className="text-accent hover:underline focus:outline-none focus:ring-2 focus:ring-border-focus rounded"
              >
                General
              </button>
            ) : (
              "General"
            )}{" "}
            to record your transcriptions here.
          </p>
        </div>
      </div>
    );
  }

  if (transcriptions.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between gap-4 mb-6">
          <h1
            className="text-text-primary font-semibold"
            style={{ fontSize: "15px", fontWeight: 600 }}
          >
            History
          </h1>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center min-h-[200px]">
          <Mic className="w-8 h-8 text-text-muted mb-3" aria-hidden />
          <p className="text-text-muted font-medium" style={{ fontWeight: 500 }}>
            No transcriptions yet
          </p>
          <p className="text-text-muted text-sm mt-1 text-center max-w-sm">
            Hold <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border font-mono text-xs">{hotkey}</kbd> to
            record your first transcription. It will appear here automatically.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex items-center justify-between gap-4 mb-6"
        style={{ marginBottom: "24px" }}
      >
        <h1
          className="text-text-primary font-semibold"
          style={{ fontSize: "15px", fontWeight: 600 }}
        >
          History
        </h1>
        <button
          type="button"
          onClick={() => setClearDialogOpen(true)}
          className="h-8 px-4 rounded-lg text-sm font-medium text-error hover:bg-error/10 border border-error/30 focus:outline-none focus:ring-2 focus:ring-border-focus"
        >
          Clear All
        </button>
      </div>

      <div className="flex flex-col">
        {groupedTranscriptions.map((group, groupIndex) => (
          <div key={group.label}>
            <div
              className="text-text-muted uppercase tracking-wider mb-2"
              style={{
                fontSize: "11px",
                letterSpacing: "0.06em",
                marginTop: groupIndex === 0 ? 0 : "24px",
                marginBottom: "8px",
              }}
            >
              {group.label}
            </div>
            {group.items.map((item) => (
              <TranscriptionItem
                key={item.id}
                item={item}
                onDelete={deleteTranscription}
              />
            ))}
          </div>
        ))}
      </div>

      <Dialog.Root open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm bg-surface border border-border rounded-lg shadow-lg p-4 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
            onPointerDownOutside={() => setClearDialogOpen(false)}
          >
            <Dialog.Title className="text-base font-semibold text-text-primary">
              Delete all transcriptions?
            </Dialog.Title>
            <Dialog.Description className="text-sm text-text-secondary mt-2">
              This cannot be undone.
            </Dialog.Description>
            <div className="flex justify-end gap-2 mt-4">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover border border-border"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="button"
                onClick={handleClearAll}
                className="h-8 px-4 rounded-lg text-sm font-medium text-error hover:bg-error/10 border border-error/30"
              >
                Delete All
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
