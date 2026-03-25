import { useEffect, useState } from "react";
import { api } from "../api";

export default function AdminUsers() {
  const [rows, setRows] = useState<
    { id: string; telegram_id: number; username: string | null; role: string; is_active: boolean; tasks_count: number }[]
  >([]);
  const [overview, setOverview] = useState<{
    total_users: number;
    total_tasks_today: number;
    success_rate_percent: number;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.adminUsers(), api.adminOverview()])
      .then(([u, o]) => {
        setRows(u);
        setOverview(o);
      })
      .catch((e: Error) => setErr(e.message));
  }, []);

  if (err) {
    return (
      <div className="space-y-2">
        <p className="text-rose-400">{err}</p>
        <p className="text-sm text-slate-500">Admin uchun JWT va admin/owner roli kerak.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Admin · Foydalanuvchilar</h1>
      {overview && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-sm">
            <span className="text-slate-500">Users</span>
            <p className="text-xl font-semibold text-white">{overview.total_users}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-sm">
            <span className="text-slate-500">Tasks today</span>
            <p className="text-xl font-semibold text-white">{overview.total_tasks_today}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-sm">
            <span className="text-slate-500">Success %</span>
            <p className="text-xl font-semibold text-emerald-400">{overview.success_rate_percent}%</p>
          </div>
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 bg-slate-900/80 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Telegram</th>
              <th className="px-4 py-2">Username</th>
              <th className="px-4 py-2">Rol</th>
              <th className="px-4 py-2">Faol</th>
              <th className="px-4 py-2">Vazifalar</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-800/80">
                <td className="px-4 py-2 font-mono">{r.telegram_id}</td>
                <td className="px-4 py-2">{r.username ?? "—"}</td>
                <td className="px-4 py-2">{r.role}</td>
                <td className="px-4 py-2">{r.is_active ? "ha" : "yo‘q"}</td>
                <td className="px-4 py-2">{r.tasks_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
