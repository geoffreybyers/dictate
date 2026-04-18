/**
 * Applies theme to the document (html element).
 * "auto" uses Tauri get_system_theme so the app matches the OS even when the WebView's matchMedia is wrong.
 */
import { useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { Theme } from "../types";

type ResolvedTheme = "light" | "dark";

function applyResolved(root: HTMLElement, resolved: ResolvedTheme): void {
  if (resolved === "light") {
    root.classList.add("light");
  } else {
    root.classList.remove("light");
  }
}

export function useTheme(theme: Theme): void {
  useEffect(() => {
    const root = document.documentElement;

    if (theme === "light" || theme === "dark") {
      applyResolved(root, theme);
      return;
    }

    // theme === "auto": resolve via Tauri so we don't rely on WebView's matchMedia
    let cancelled = false;
    invoke<ResolvedTheme>("get_system_theme")
      .then((resolved) => {
        if (!cancelled) applyResolved(root, resolved);
      })
      .catch(() => {
        if (!cancelled) applyResolved(root, "dark");
      });

    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const listener = () => {
      if (cancelled) return;
      invoke<ResolvedTheme>("get_system_theme")
        .then((resolved) => applyResolved(root, resolved))
        .catch(() => applyResolved(root, "dark"));
    };
    mq.addEventListener("change", listener);

    return () => {
      cancelled = true;
      mq.removeEventListener("change", listener);
    };
  }, [theme]);
}
