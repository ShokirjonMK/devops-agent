import { useEffect, useRef, useState } from "react";

/**
 * Vazifa bo‘yicha Redis orqali keladigan JSON qatorlarini WebSocket dan o‘qiydi.
 * Vite dev: /api/ws proxy orqali; production: nginx /api/ws/.
 */
export function useTaskStream(taskId: number | null): string[] {
  const [lines, setLines] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${window.location.host}/api/ws/tasks/${taskId}/stream`;

    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onmessage = (ev: MessageEvent<string>) => {
      setLines((prev) => [...prev, ev.data]);
    };
    ws.onerror = () => {
      /* proxy yoki API o‘chiq */
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [taskId]);

  return lines;
}
