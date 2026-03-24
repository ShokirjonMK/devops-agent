import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Task } from "../api";

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [cmd, setCmd] = useState("");
  const [serverId, setServerId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .listTasks()
      .then(setTasks)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  const active = tasks.filter((t) => t.status === "pending" || t.status === "running").length;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cmd.trim()) return;
    setSubmitting(true);
    setErr(null);
    try {
      const sid = serverId ? Number(serverId) : null;
      await api.createTask(cmd.trim(), sid);
      setCmd("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const badge = (s: string) => {
    const map: Record<string, string> = {
      pending: "bg-amber-500/20 text-amber-300",
      running: "bg-sky-500/20 text-sky-300",
      done: "bg-emerald-500/20 text-emerald-300",
      error: "bg-rose-500/20 text-rose-300",
    };
    return map[s] || "bg-slate-700 text-slate-300";
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="mt-1 text-slate-400">
          Tabiiy til buyrug‘i yuboring — agent serverni aniqlaydi, SSH orqali diagnostika va tuzatishni bajaradi. O‘z AI
          kalitingizni ishlatish uchun JWT saqlang (AI kalitlar sahifasi) — shunda vazifa sizga bog‘lanadi.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Faol vazifalar</p>
          <p className="mt-1 text-2xl font-semibold text-white">{active}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Jami (oxirgi 100)</p>
          <p className="mt-1 text-2xl font-semibold text-white">{tasks.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-sm text-slate-500">Holat</p>
          <p className="mt-1 text-sm text-emerald-400">API + worker ishlamoqda</p>
        </div>
      </div>

      <form
        onSubmit={submit}
        className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/20"
      >
        <h2 className="text-lg font-medium text-white">Yangi buyruq</h2>
        <textarea
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          rows={3}
          placeholder="Masalan: sarbon serverida nginx ishlamayapti"
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
        />
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-slate-500">server_id (ixtiyoriy)</label>
            <input
              type="number"
              className="mt-1 w-40 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
              value={serverId}
              onChange={(e) => setServerId(e.target.value)}
              placeholder="avtomatik"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {submitting ? "Yuborilmoqda…" : "Yuborish"}
          </button>
        </div>
        {err && <p className="text-sm text-rose-400">{err}</p>}
      </form>

      <div>
        <h2 className="mb-3 text-lg font-medium text-white">Vazifalar</h2>
        {loading && tasks.length === 0 ? (
          <p className="text-slate-500">Yuklanmoqda…</p>
        ) : (
          <ul className="space-y-2">
            {tasks.map((t) => (
              <li key={t.id}>
                <Link
                  to={`/tasks/${t.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 transition hover:border-slate-600"
                >
                  <div>
                    <p className="font-mono text-sm text-slate-200">{t.command_text}</p>
                    <p className="text-xs text-slate-500">
                      #{t.id} · {new Date(t.created_at).toLocaleString()}
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge(t.status)}`}>
                    {t.status}
                  </span>
                </Link>
              </li>
            ))}
            {tasks.length === 0 && <p className="text-slate-500">Hali vazifa yo‘q.</p>}
          </ul>
        )}
      </div>
    </div>
  );
}
