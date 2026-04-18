/**
 * Persistent header: drag region + window controls. Status lives in sidebar footer.
 */
import { getCurrentWindow } from "@tauri-apps/api/window";

export function Header() {
  const handleMinimize = () => {
    getCurrentWindow().minimize();
  };

  const handleMaximize = async () => {
    const w = getCurrentWindow();
    const isMaximized = await w.isMaximized();
    if (isMaximized) w.unmaximize();
    else w.maximize();
  };

  const handleClose = () => {
    getCurrentWindow().close();
  };

  const handleTitleBarMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    if (e.detail !== 1) return;
    if ((e.target as HTMLElement).closest("button")) return;
    getCurrentWindow().startDragging();
  };

  const handleTitleBarDoubleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest("button")) return;
    getCurrentWindow().toggleMaximize();
  };

  return (
    <header
      className="h-header flex items-center justify-end border-b border-border bg-background flex-shrink-0 cursor-grab active:cursor-grabbing select-none"
      style={{ height: "52px" }}
      onMouseDown={handleTitleBarMouseDown}
      onDoubleClick={handleTitleBarDoubleClick}
    >
      <div className="flex items-center pr-5 gap-0.5 flex-shrink-0" style={{ paddingRight: "20px" }}>
        <button
          type="button"
          onClick={handleMinimize}
          className="w-7 h-7 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-md transition-colors"
          aria-label="Minimize"
        >
          ─
        </button>
        <button
          type="button"
          onClick={handleMaximize}
          className="w-7 h-7 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-md transition-colors"
          aria-label="Maximize"
        >
          □
        </button>
        <button
          type="button"
          onClick={handleClose}
          className="w-7 h-7 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-error/15 rounded-md transition-colors"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
    </header>
  );
}
