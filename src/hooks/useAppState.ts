/**
 * App state from sidecar events (Tauri emits sidecar_event with payload).
 * State machine: loading → ready ↔ recording → transcribing → ready (error from any state).
 */
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { AppState as AppStateStatus, SessionType, SidecarMessage } from "../types";

/** Return type of useAppState: full app state snapshot. */
export interface AppStateSnapshot {
  status: AppStateStatus;
  queueDepth: number;
  modelReady: boolean;
  cudaAvailable: boolean;
  sessionType: SessionType;
  /** PID of sidecar process when running (from ready payload if present). */
  pid: number | null;
  /** Version string from sidecar ready message. */
  sidecarVersion: string | null;
  /** CUDA version string when available (e.g. "CUDA 12.1"). Not in ready yet — placeholder. */
  cudaVersion: string | null;
  error: { code: string; message?: string } | null;
  lastResult: {
    text: string;
    durationMs: number;
    transcriptionMs?: number | null;
    confidence?: number | null;
    detected_language?: string | null;
  } | null;
}

const initialState: AppStateSnapshot = {
  status: "loading",
  queueDepth: 0,
  modelReady: false,
  cudaAvailable: false,
  sessionType: "unknown",
  pid: null,
  sidecarVersion: null,
  cudaVersion: null,
  error: null,
  lastResult: null,
};

export function useAppState(): AppStateSnapshot {
  const [state, setState] = useState<AppStateSnapshot>(initialState);

  useEffect(() => {
    const unlisten = listen<SidecarMessage>("sidecar_event", (event) => {
      const payload = event.payload;
      if (!payload || typeof payload !== "object" || !("type" in payload)) return;
      const type = (payload as { type: string }).type;

      if (type === "ready" && typeof import.meta !== "undefined" && import.meta.env?.DEV) {
        console.log("[useAppState] sidecar_event ready", payload);
      }
      setState((prev) => {
        const next = { ...prev };
        switch (type) {
          case "ready": {
            const r = payload as {
              device: string;
              model: string;
              cuda_available?: boolean;
              session_type?: SessionType;
              sidecar_version?: string;
              pid?: number;
              cuda_version?: string;
            };
            next.modelReady = true;
            next.cudaAvailable = r.cuda_available ?? false;
            next.sessionType = r.session_type ?? "unknown";
            next.sidecarVersion = r.sidecar_version ?? null;
            next.pid = r.pid ?? null;
            next.cudaVersion = r.cuda_version ?? null;
            next.error = null;
            next.status = "ready";
            break;
          }
          case "model_loading":
            next.modelReady = false;
            next.status = "loading";
            break;
          case "model_ready":
            next.modelReady = true;
            next.status = "ready";
            break;
          case "recording_started":
            next.status = "recording";
            next.error = null;
            break;
          case "recording_stopped":
            next.status = prev.queueDepth > 0 ? "transcribing" : "ready";
            break;
          case "transcribing": {
            const t = payload as { queue_depth?: number };
            next.queueDepth = t.queue_depth ?? 0;
            next.status = "transcribing";
            break;
          }
          case "transcription_complete": {
            const t = payload as {
              text: string;
              duration_ms?: number;
              transcription_ms?: number;
              confidence?: number;
              detected_language?: string;
            };
            next.lastResult = {
              text: t.text,
              durationMs: t.duration_ms ?? 0,
              transcriptionMs: t.transcription_ms ?? null,
              confidence: t.confidence ?? null,
              detected_language: t.detected_language ?? null,
            };
            next.queueDepth = Math.max(0, prev.queueDepth - 1);
            next.status = next.queueDepth > 0 ? "transcribing" : "ready";
            break;
          }
          case "transcription_empty":
            next.queueDepth = Math.max(0, prev.queueDepth - 1);
            next.status = next.queueDepth > 0 ? "transcribing" : "ready";
            break;
          case "error": {
            const e = payload as { code: string; message?: string };
            next.error = { code: e.code, message: e.message };
            next.status = "error";
            break;
          }
          default:
            break;
        }
        return next;
      });
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  // Sync tray icon with status (Tauri command).
  useEffect(() => {
    invoke("set_tray_status", { status: state.status }).catch(() => {});
  }, [state.status]);

  return state;
}
