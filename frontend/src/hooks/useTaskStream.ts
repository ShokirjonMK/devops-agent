import { useEffect, useRef, useState } from "react";
import { getStoredToken } from "../api";

export type StreamState = "connecting" | "connected" | "reconnecting" | "closed";

export type TaskStreamEvent = {
  type: string;
  raw: string;
  data: Record<string, unknown>;
};

/**
 * WebSocket: `/ws/tasks/{id}?token=` — qayta ulanish 1s … 30s.
 */
export function useTaskStream(taskId: number | null): {
  events: TaskStreamEvent[];
  lines: string[];
  state: StreamState;
} {
  const [events, setEvents] = useState<TaskStreamEvent[]>([]);
  const [lines, setLines] = useState<string[]>([]);
  const [state, setState] = useState<StreamState>("closed");
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const token = getStoredToken();
    const base = `${proto}//${window.location.host}/ws/tasks/${taskId}`;
    const url = token ? `${base}?token=${encodeURIComponent(token)}` : base;

    const clearTimer = () => {
      if (timerRef.current != null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const pushParsed = (raw: string, data: Record<string, unknown>) => {
      const t = String(data.type ?? "message");
      if (t === "ping") return;
      setEvents((prev) => [...prev.slice(-199), { type: t, raw, data }]);
      setLines((prev) => [...prev.slice(-199), raw]);
    };

    const connect = () => {
      if (cancelled) return;
      setState(attemptRef.current === 0 ? "connecting" : "reconnecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        if (cancelled) return;
        attemptRef.current = 0;
        setState("connected");
      };
      ws.onmessage = (ev: MessageEvent<string>) => {
        const raw = ev.data;
        try {
          const data = JSON.parse(raw) as Record<string, unknown>;
          pushParsed(raw, data);
        } catch {
          setLines((prev) => [...prev.slice(-199), raw]);
        }
      };
      ws.onerror = () => {};
      ws.onclose = () => {
        wsRef.current = null;
        if (cancelled) return;
        setState("closed");
        attemptRef.current += 1;
        const delay = Math.min(30000, 1000 * Math.pow(2, Math.min(attemptRef.current - 1, 5)));
        timerRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearTimer();
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [taskId]);

  return { events, lines, state };
}
