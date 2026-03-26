import { Link } from "react-router-dom";
import type { Server } from "../api";

type Props = {
  server: Server;
  metrics?: { cpu: number | null; ram: number | null; disk: number | null } | null;
  onQuickTask?: (serverId: number) => void;
};

function chip(status: string | undefined) {
  const s = status || "unknown";
  if (s === "online") return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
  if (s === "offline") return "bg-rose-500/20 text-rose-300 border-rose-500/30";
  if (s === "warning") return "bg-amber-500/20 text-amber-200 border-amber-500/30";
  return "bg-slate-700/60 text-slate-400 border-slate-600";
}

function MiniBar({ label, v }: { label: string; v: number | null | undefined }) {
  const pct = v == null || Number.isNaN(v) ? 0 : Math.min(100, Math.max(0, v));
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px] uppercase tracking-wide text-slate-500">
        <span>{label}</span>
        <span>{v == null ? "—" : `${pct.toFixed(0)}%`}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-sky-500/80 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function ServerCard({ server, metrics, onQuickTask }: Props) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-white">{server.name}</h3>
          <p className="font-mono text-xs text-slate-500">{server.host}</p>
          <p className="text-xs text-slate-600">
            {server.user} · {server.environment ?? "production"}
          </p>
        </div>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${chip(server.last_check_status)}`}>
          {server.last_check_status ?? "unknown"}
        </span>
      </div>
      {metrics && (
        <div className="space-y-2">
          <MiniBar label="CPU" v={metrics.cpu} />
          <MiniBar label="RAM" v={metrics.ram} />
          <MiniBar label="Disk" v={metrics.disk} />
        </div>
      )}
      <div className="mt-auto flex flex-wrap gap-2 pt-1">
        <Link
          to="/"
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-emerald-500/50 hover:text-emerald-300"
        >
          Dashboard
        </Link>
        {onQuickTask && (
          <button
            type="button"
            onClick={() => onQuickTask(server.id)}
            className="rounded-lg bg-emerald-600/90 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500"
          >
            Vazifa yuborish
          </button>
        )}
      </div>
    </div>
  );
}
