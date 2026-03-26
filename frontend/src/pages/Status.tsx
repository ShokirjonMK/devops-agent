import { useEffect, useState } from "react";

type StatusData = {
  status: string;
  updated_at: string;
  components: Record<string, string>;
  uptime_90d_percent: number;
  incidents: unknown[];
};

const STATUS_LABELS: Record<string, { label: string; color: string; dot: string }> = {
  operational: { label: "Ishlamoqda", color: "text-emerald-400", dot: "bg-emerald-500" },
  degraded_performance: { label: "Sekin ishlayapti", color: "text-yellow-400", dot: "bg-yellow-500" },
  partial_outage: { label: "Qisman ishlamayapti", color: "text-orange-400", dot: "bg-orange-500" },
  major_outage: { label: "Ishlamayapti", color: "text-red-400", dot: "bg-red-500" },
};

export default function Status() {
  const [data, setData] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));

    const iv = setInterval(() => {
      fetch("/api/status")
        .then((r) => r.json())
        .then(setData)
        .catch(() => {});
    }, 30_000);
    return () => clearInterval(iv);
  }, []);

  const overall = data ? (STATUS_LABELS[data.status] || STATUS_LABELS["major_outage"]) : null;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Tizim Holati</h1>
        <p className="text-slate-400">Barcha komponentlar holati real vaqtda</p>
      </div>

      {loading ? (
        <div className="text-center text-slate-500 py-16">Yuklanmoqda…</div>
      ) : data ? (
        <div className="space-y-4">
          {/* Overall status */}
          <div className={`rounded-xl border p-6 text-center ${
            data.status === "operational"
              ? "border-emerald-500/40 bg-emerald-500/10"
              : data.status === "major_outage"
              ? "border-red-500/40 bg-red-500/10"
              : "border-yellow-500/40 bg-yellow-500/10"
          }`}>
            <div className="flex items-center justify-center gap-3 mb-2">
              <div className={`w-4 h-4 rounded-full ${overall?.dot} animate-pulse`} />
              <span className={`text-2xl font-bold ${overall?.color}`}>{overall?.label}</span>
            </div>
            <div className="text-sm text-slate-400">
              Yangilandi: {new Date(data.updated_at).toLocaleTimeString("uz-UZ")}
            </div>
          </div>

          {/* Uptime */}
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 flex items-center justify-between">
            <span className="text-slate-300 text-sm">So'nggi 90 kun uptime</span>
            <span className="text-emerald-400 font-semibold">{data.uptime_90d_percent.toFixed(1)}%</span>
          </div>

          {/* Components */}
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 divide-y divide-slate-700">
            {Object.entries(data.components).map(([name, status]) => {
              const s = STATUS_LABELS[status] || STATUS_LABELS["major_outage"];
              return (
                <div key={name} className="flex items-center justify-between px-5 py-3">
                  <span className="text-white text-sm font-medium">{name}</span>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${s.dot}`} />
                    <span className={`text-sm ${s.color}`}>{s.label}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {data.incidents.length === 0 && (
            <div className="text-center text-slate-500 text-sm py-4">
              Hozirda hech qanday hodisa yo'q
            </div>
          )}
        </div>
      ) : (
        <div className="text-center text-red-400 py-16">Ma'lumot yuklanmadi</div>
      )}
    </div>
  );
}
