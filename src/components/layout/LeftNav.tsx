/**
 * Left navigation: flat list of nav items — General, Advanced, Model, History.
 * Fixed width 220px; active item has left accent border.
 * Footer shows status (Hold hotkey…, Recording…, Copied…, etc.).
 */
import { Settings, Bot, Code2, MessageSquare } from "lucide-react";
import type { NavScreen } from "../../types";
import { SidebarStatus } from "./SidebarStatus";

interface LeftNavProps {
  activeScreen: NavScreen;
  onSelect: (screen: NavScreen) => void;
  hotkey: string;
  lastResult: { text: string; durationMs: number } | null;
}

const NAV_ITEMS: { screen: NavScreen; label: string; icon: typeof Settings }[] = [
  { screen: "general", label: "General", icon: Settings },
  { screen: "advanced", label: "Advanced", icon: Code2 },
  { screen: "model", label: "Model", icon: Bot },
  { screen: "history", label: "History", icon: MessageSquare },
];

export function LeftNav({ activeScreen, onSelect, hotkey, lastResult }: LeftNavProps) {
  return (
    <nav
      className="w-nav flex flex-col h-full bg-background border-r border-border flex-shrink-0"
      style={{ width: "220px" }}
      aria-label="Main navigation"
    >
      <div className="flex-1 min-h-0 overflow-y-auto py-4 px-3">
        {NAV_ITEMS.map(({ screen, label, icon: Icon }) => (
          <button
            key={screen}
            type="button"
            onClick={() => onSelect(screen)}
            className={`h-nav-item flex items-center gap-2.5 px-2.5 rounded-lg transition-colors duration-100 ${
              activeScreen === screen
                ? "bg-surface text-text-primary border-l-2 border-accent"
                : "text-text-secondary hover:bg-surface-hover border-l-2 border-transparent"
            }`}
            style={{
              minHeight: "36px",
              borderLeftWidth: "2px",
              marginLeft: "-2px",
              paddingLeft: "10px",
            }}
          >
            <Icon className="w-4 h-4 shrink-0" style={{ color: "inherit" }} />
            <span className="text-sm">{label}</span>
          </button>
        ))}
      </div>
      <SidebarStatus hotkey={hotkey} lastResult={lastResult} />
    </nav>
  );
}
