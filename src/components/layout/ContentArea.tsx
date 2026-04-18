/**
 * Scrollable content area: padding 32px, max-width 560px centered.
 */
import type { ReactNode } from "react";

interface ContentAreaProps {
  children: ReactNode;
}

export function ContentArea({ children }: ContentAreaProps) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div
        className="mx-auto w-full max-w-content py-0 px-content"
        style={{ maxWidth: "560px", padding: "32px" }}
      >
        {children}
      </div>
    </div>
  );
}
