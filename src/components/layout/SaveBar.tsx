/**
 * Floating save bar: appears when there are unsaved changes on a settings screen.
 * Not shown on Developer or Transcriptions screens.
 * Slides up from bottom (200ms ease-out), dismisses down (150ms ease-in).
 */
interface SaveBarProps {
  visible: boolean;
  onDiscard: () => void;
  onSave: () => void;
  saving: boolean;
  saved?: boolean;
}

export function SaveBar({ visible, onDiscard, onSave, saving, saved = false }: SaveBarProps) {
  return (
    <div
      className="flex items-center justify-between border-t border-border bg-surface px-content py-3 transition-transform duration-200 ease-out"
      style={{
        paddingTop: "12px",
        paddingBottom: "12px",
        paddingLeft: "32px",
        paddingRight: "32px",
        transform: visible ? "translateY(0)" : "translateY(100%)",
      }}
      role="region"
      aria-label="Unsaved changes"
      aria-hidden={!visible}
    >
      <span className="text-sm text-text-muted">You have unsaved changes</span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onDiscard}
          disabled={saving}
          className="h-8 px-4 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-hover border border-border transition-colors disabled:opacity-50"
        >
          Discard
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="h-8 px-4 rounded-lg text-sm font-medium bg-accent text-on-accent hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          {saved ? "Saved ✓" : saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
