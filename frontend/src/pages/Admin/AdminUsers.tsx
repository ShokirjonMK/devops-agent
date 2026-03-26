import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { api } from "../../api";

type Row = {
  id: string;
  telegram_id: number;
  username: string | null;
  role: string;
  is_active: boolean;
  tasks_count: number;
  servers_count?: number;
};

const ROLES = ["viewer", "operator", "admin", "owner"] as const;

export default function AdminUsers() {
  const [rows, setRows] = useState<Row[]>([]);
  const [overview, setOverview] = useState<{
    total_users: number;
    total_tasks_today: number;
    success_rate_percent: number;
    total_ai_cost_month_usd?: number;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = () =>
    Promise.all([api.adminUsers(), api.adminOverview()])
      .then(([u, o]) => {
        setRows(u as Row[]);
        setOverview(o);
      })
      .catch((e: Error) => setErr(e.message));

  useEffect(() => {
    load();
  }, []);

  const patchRole = async (id: string, role: string) => {
    setErr(null);
    try {
      await api.adminSetUserRole(id, role);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const patchActive = async (id: string, is_active: boolean) => {
    setErr(null);
    try {
      await api.adminSetUserActive(id, is_active);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (err && rows.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-rose-400">{err}</p>
        <p className="text-sm text-slate-500">Admin uchun JWT va admin/owner roli kerak.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap gap-3 text-xs text-slate-500">
        <span className="text-emerald-400">Users</span>
        <NavLink className="hover:text-white" to="/admin/stats">
          Stats
        </NavLink>
        <NavLink className="hover:text-white" to="/admin/settings">
          Settings
        </NavLink>
        <NavLink className="hover:text-white" to="/admin/ai">
          System AI
        </NavLink>
        <NavLink className="hover:text-white" to="/admin/audit">
          Audit
        </NavLink>
      </nav>
      <h1 className="text-2xl font-semibold text-white">Admin · Foydalanuvchilar</h1>
      {err && <p className="text-sm text-rose-400">{err}</p>}
      {overview && (
        <div className="grid gap-3 sm:grid-cols-4">
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
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-sm">
            <span className="text-slate-500">AI oy</span>
            <p className="text-xl font-semibold text-violet-300">
              ${(overview.total_ai_cost_month_usd ?? 0).toFixed(2)}
            </p>
          </div>
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[640px] text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 bg-slate-900/80 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Telegram</th>
              <th className="px-4 py-2">Username</th>
              <th className="px-4 py-2">Rol</th>
              <th className="px-4 py-2">Faol</th>
              <th className="px-4 py-2">Vazifalar</th>
              <th className="px-4 py-2">Serverlar*</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-800/80">
                <td className="px-4 py-2 font-mono">{r.telegram_id}</td>
                <td className="px-4 py-2">{r.username ?? "—"}</td>
                <td className="px-4 py-2">
                  <select
                    className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
                    value={r.role}
                    onChange={(e) => patchRole(r.id, e.target.value)}
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2">
                  <button
                    type="button"
                    className={`text-xs underline ${r.is_active ? "text-emerald-400" : "text-rose-400"}`}
                    onClick={() => patchActive(r.id, !r.is_active)}
                  >
                    {r.is_active ? "faol" : "blok"}
                  </button>
                </td>
                <td className="px-4 py-2">{r.tasks_count}</td>
                <td className="px-4 py-2 text-slate-500">{r.servers_count ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="px-4 py-2 text-xs text-slate-600">* Foydalanuvchi vazifalarida ishlatilgan noyob serverlar.</p>
      </div>
    </div>
  );
}
