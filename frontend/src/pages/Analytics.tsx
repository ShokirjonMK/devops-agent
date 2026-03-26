import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Server } from "../api";

const HEAT_COLORS = ["bg-slate-900", "bg-emerald-900/50", "bg-emerald-700/60", "bg-emerald-500/80", "bg-emerald-400"];

export default function Analytics() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.analyticsSummary>> | null>(null);
  const [servers, setServers] = useState<Server[]>([]);
  const [selServer, setSelServer] = useState<number | "">("");
  const [series, setSeries] = useState<{ t: string | null; cpu: number | null; ram: number | null; disk: number | null }[]>(
    []
  );
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .analyticsSummary()
      .then(setData)
      .catch((e: Error) => setErr(e.message));
    api.listServers().then(setServers).catch(() => {});
  }, []);

  useEffect(() => {
    if (selServer === "" || typeof selServer !== "number") {
      setSeries([]);
      return;
    }
    api
      .analyticsServerMetrics(selServer, 168)
      .then((r) => setSeries(r.points))
      .catch(() => setSeries([]));
  }, [selServer]);

  if (err) return <p className="text-rose-400">{err}</p>;
  if (!data) return <p className="text-slate-500">Yuklanmoqda…</p>;

  const heatMax = Math.max(1, ...data.activity_heatmap.map((h) => h.count));
  const heatLevel = (c: number) => {
    if (c <= 0) return 0;
    const r = c / heatMax;
    if (r < 0.2) return 1;
    if (r < 0.45) return 2;
    if (r < 0.7) return 3;
    return 4;
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-white">Analytics</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Jami vazifalar (30 kun)</p>
          <p className="mt-1 text-2xl font-semibold text-white">{data.tasks_total_30d}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Success rate</p>
          <p className="mt-1 text-2xl font-semibold text-emerald-400">{data.success_rate_percent}%</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Server uptime (online/all)</p>
          <p className="mt-1 text-2xl font-semibold text-sky-300">{data.uptime_percent}%</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Mening AI xarajatim (oy)</p>
          <p className="mt-1 text-2xl font-semibold text-violet-300">${data.ai_cost_month_usd.toFixed(4)}</p>
        </div>
      </div>

      <div className="h-72 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-medium text-slate-400">Kun bo‘yicha (success vs error)</h2>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={data.series_tasks_by_day}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="day" stroke="#94a3b8" fontSize={10} />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Legend />
            <Line type="monotone" dataKey="ok" name="done" stroke="#34d399" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="bad" name="error" stroke="#fb7185" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-64 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h2 className="mb-2 text-sm font-medium text-slate-400">AI xarajat provayder bo‘yicha</h2>
          <ResponsiveContainer width="100%" height="90%">
            <PieChart>
              <Pie
                data={data.ai_cost_by_provider}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={72}
                label={({ name, value }) => `${name}: $${Number(value).toFixed(3)}`}
              >
                {data.ai_cost_by_provider.map((_, i) => (
                  <Cell key={i} fill={["#34d399", "#38bdf8", "#a78bfa", "#fb7185", "#fbbf24"][i % 5]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="h-64 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h2 className="mb-2 text-sm font-medium text-slate-400">Server holati (so‘nggi check)</h2>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={data.server_uptime_bars}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} interval={0} angle={-25} textAnchor="end" height={60} />
              <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
              <Bar dataKey="uptime_score" fill="#34d399" name="online %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="text-sm font-medium text-slate-400">CPU / RAM / Disk (Area)</h2>
          <select
            className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
            value={selServer}
            onChange={(e) => setSelServer(e.target.value === "" ? "" : Number(e.target.value))}
          >
            <option value="">Server tanlang</option>
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        {series.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="t" tickFormatter={(v) => (v ? String(v).slice(5, 16) : "")} stroke="#94a3b8" fontSize={9} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                <Legend />
                <Area type="monotone" dataKey="cpu" stackId="1" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.35} name="CPU" />
                <Area type="monotone" dataKey="ram" stackId="2" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.35} name="RAM" />
                <Area type="monotone" dataKey="disk" stackId="3" stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.35} name="Disk" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Server va monitoring yoqilgan bo‘lsa, grafik paydo bo‘ladi.</p>
        )}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-400">Faollik (sizning vazifalaringiz)</h2>
        <div className="flex flex-wrap gap-1">
          {data.activity_heatmap.slice(-56).map((h) => (
            <div
              key={h.day}
              title={`${h.day}: ${h.count}`}
              className={`h-4 w-4 rounded-sm ${HEAT_COLORS[heatLevel(h.count)]}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
