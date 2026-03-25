import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Task } from "../api";

export default function Analytics() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTasks()
      .then(setTasks)
      .catch((e: Error) => setErr(e.message));
  }, []);

  const byDay = () => {
    const m = new Map<string, { day: string; ok: number; bad: number }>();
    for (const t of tasks) {
      const d = new Date(t.created_at).toISOString().slice(0, 10);
      if (!m.has(d)) m.set(d, { day: d, ok: 0, bad: 0 });
      const row = m.get(d)!;
      if (t.status === "done") row.ok += 1;
      if (t.status === "error") row.bad += 1;
    }
    return [...m.values()].sort((a, b) => a.day.localeCompare(b.day)).slice(-30);
  };

  const successRate = () => {
    const ok = tasks.filter((t) => t.status === "done").length;
    const all = tasks.length || 1;
    return Math.round((100 * ok) / all);
  };

  if (err) return <p className="text-rose-400">{err}</p>;

  const chartData = byDay();

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-white">Analytics</h1>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Jami vazifalar (100)</p>
          <p className="mt-1 text-2xl font-semibold text-white">{tasks.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Success rate</p>
          <p className="mt-1 text-2xl font-semibold text-emerald-400">{successRate()}%</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Oy AI xarajati</p>
          <p className="mt-1 text-2xl font-semibold text-slate-300">—</p>
        </div>
      </div>

      <div className="h-72 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-medium text-slate-400">Kun bo‘yicha (oxirgi 30)</h2>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="day" stroke="#94a3b8" fontSize={11} />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Legend />
            <Line type="monotone" dataKey="ok" name="done" stroke="#34d399" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="bad" name="error" stroke="#fb7185" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="h-64 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-medium text-slate-400">Bar (done vs error)</h2>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={chartData.slice(-14)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="day" stroke="#94a3b8" fontSize={10} />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Bar dataKey="ok" fill="#34d399" name="done" />
            <Bar dataKey="bad" fill="#fb7185" name="error" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
