/**
 * Titled settings group with divider. Use section-gap (32px) between groups.
 */
import type { ReactNode } from "react";

interface SettingGroupProps {
  title: string;
  children: ReactNode;
}

export function SettingGroup({ title, children }: SettingGroupProps) {
  return (
    <div>
      <h2
        className="text-text-secondary font-medium border-b border-border pb-0 mb-4"
        style={{ fontSize: "12px", borderBottomWidth: "1px" }}
      >
        {title}
      </h2>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}
