/**
 * Single setting row: label, optional helper, control(s). Inline or stacked layout.
 */
import type { ReactNode } from "react";

interface SettingRowProps {
  label: string;
  helper?: string;
  layout: "inline" | "stacked";
  children: ReactNode;
}

export function SettingRow({ label, helper, layout, children }: SettingRowProps) {
  const labelBlock = (
    <div>
      <span className="text-text-primary" style={{ fontSize: "13px" }}>
        {label}
      </span>
      {helper != null && (
        <p
          className="text-text-muted mt-0.5"
          style={{ fontSize: "11px", marginTop: "2px" }}
        >
          {helper}
        </p>
      )}
    </div>
  );

  if (layout === "inline") {
    return (
      <div
        className="flex items-center justify-between gap-4 min-h-[44px]"
        style={{ minHeight: "44px" }}
      >
        {labelBlock}
        <div className="shrink-0">{children}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {labelBlock}
      <div className="w-full">{children}</div>
    </div>
  );
}
