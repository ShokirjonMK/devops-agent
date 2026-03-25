import { useEffect, useRef, useState } from "react";
import { getStoredToken } from "../api";

export type StreamState = "connecting" | "connected" | "reconnecting" | "closed";

/**
 * Vazifa hodisalari: WebSocket + JWT (ixtiyoriy). Token bo‘lsa `?token=` qo‘shiladi.
 * Qayta ulanish: 1s, 2s, 4s … max 30s.
 */
export function useTaskStream(taskId: number | null): { lines: string[]; state: StreamState } {
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
    const base = `${proto}//${window.location.host}/api/ws/tasks/${taskId}/stream`;
    const url = token ? `${base}?token=${encodeURIComponent(token)}` : base;

    const clearTimer = () => {
      if (timerRef.current != null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
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
        try {
          const j = JSON.parse(ev.data) as { type?: string };
          if (j.type === "ping") return;
        } catch {
          /* matn */
        }
        setLines((prev) => [...prev, ev.data]);
      };
      ws.onerror = () => {
        /* proxy yoki API */
      };
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

  return { lines, state };
}
