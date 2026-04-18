/**
 * Provides a single useSettings instance to the app so all screens share the same state.
 */
import { createContext, useContext, type ReactNode } from "react";
import type { UseSettingsReturn } from "../hooks/useSettings";

const SettingsContext = createContext<UseSettingsReturn | null>(null);

export function SettingsProvider({
  value,
  children,
}: {
  value: UseSettingsReturn;
  children: ReactNode;
}) {
  return (
    <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
  );
}

export function useSettingsContext(): UseSettingsReturn {
  const ctx = useContext(SettingsContext);
  if (ctx == null) {
    throw new Error("useSettingsContext must be used within SettingsProvider");
  }
  return ctx;
}
