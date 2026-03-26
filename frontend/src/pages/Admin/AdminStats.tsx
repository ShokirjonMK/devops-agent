import { useEffect, useState } from "react";
import { api } from "../../api";

export default function AdminStats() {
  const [o, setO] = useState<{
    total_users: number;
    active_users_today: number;
    total_tasks_today: number;
    total_tasks_week: number;
    success_rate_percent: number;
    total_ai_cost_month_usd: number;
    total_servers: number;
    servers_online: number;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.adminOverview().then(setO).catch((e: Error) => setErr(e.message));
  }, []);

  if (err) return <p className="text-rose-400">{err}</p>;
  if (!o) return <p className="text-slate-500">Yuklanmoqda…</p>;

  const cards = [
    { label: "Foydalanuvchilar", value: o.total_users },
    { label: "Bugun faol", value: o.active_users_today },
    { label: "Vazifalar (bugun)", value: o.total_tasks_today },
    { label: "Vazifalar (hafta)", value: o.total_tasks_week },
    { label: "Success %", value: `${o.success_rate_percent}%` },
    { label: "AI xarajat (oy)", value: `$${o.total_ai_cost_month_usd.toFixed(2)}` },
    { label: "Serverlar", value: o.total_servers },
    { label: "Online serverlar", value: o.servers_online },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Admin · Statistika</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{c.label}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{c.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
