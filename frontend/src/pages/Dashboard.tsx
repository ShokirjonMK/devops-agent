import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Server, type Task } from "../api";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-amber-500/20 text-amber-300",
  running: "bg-sky-500/20 text-sky-300 animate-pulse",
  done: "bg-emerald-500/20 text-emerald-300",
  error: "bg-rose-500/20 text-rose-300",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Navbatda",
  running: "Ishlayapti",
  done: "Bajarildi",
  error: "Xato",
};

const EXAMPLES = [
  "nginx ishlamayapti, qayta ishga tushur",
  "disk to'lib qolgan, eski loglarni tozala",
  "mysql sekin, muammo nima",
  "server xotirasi 90% dan oshdi",
];

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [cmd, setCmd] = useState("");
  const [serverId, setServerId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const loadTasks = () =>
    api
      .listTasks()
      .then(setTasks)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));

  useEffect(() => {
    api.listServers().then(setServers).catch(() => {});
    loadTasks();
    const t = setInterval(loadTasks, 5000);
    return () => clearInterval(t);
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cmd.trim()) return;
    setSubmitting(true);
    setErr(null);
    try {
      const sid = serverId ? Number(serverId) : null;
      await api.createTask(cmd.trim(), sid);
      setCmd("");
      loadTasks();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const active = tasks.filter((t) => t.status === "pending" || t.status === "running").length;
  const done = tasks.filter((t) => t.status === "done").length;
  const errors = tasks.filter((t) => t.status === "error").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="mt-1 text-slate-400">
          Serverlaringizni tabiiy til orqali boshqaring. Oddiy so'z bilan buyruq yuboring — agent SSH orqali bajaradi.
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        {[
          { label: "Faol", value: active, color: active > 0 ? "text-sky-400" : "text-white" },
          { label: "Bajarildi", value: done, color: "text-emerald-400" },
          { label: "Xato", value: errors, color: errors > 0 ? "text-rose-400" : "text-white" },
          { label: "Serverlar", value: servers.length, color: "text-purple-400" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <p className="text-xs text-slate-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Command form */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-base font-medium text-white mb-3">Buyruq yuborish</h2>

        {servers.length === 0 && (
          <div className="mb-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-300">
            Hali server qo'shilmagan.{" "}
            <a href="/servers" className="underline hover:text-yellow-200">
              Serverlar sahifasida qo'shing →
            </a>
          </div>
        )}

        <form onSubmit={submit} className="space-y-3">
          <div>
            <textarea
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              rows={3}
              placeholder="Masalan: nginx ishlamayapti, qayta ishga tushur"
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
            />
            {/* Quick examples */}
            <div className="flex flex-wrap gap-1 mt-1.5">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => setCmd(ex)}
                  className="rounded-full border border-slate-700 px-2 py-0.5 text-xs text-slate-500 hover:border-slate-500 hover:text-slate-300 transition"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-40">
              <label className="block text-xs text-slate-500 mb-1">Server (ixtiyoriy)</label>
              <select
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none"
                value={serverId}
                onChange={(e) => setServerId(e.target.value)}
              >
                <option value="">Avtomatik aniqlash</option>
                {servers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.host})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={submitting || !cmd.trim()}
              className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 transition"
            >
              {submitting ? "Yuborilmoqda…" : "Yuborish →"}
            </button>
          </div>

          {err && <p className="text-sm text-rose-400">{err}</p>}
        </form>
      </div>

      {/* Tasks list */}
      <div>
        <h2 className="mb-3 text-base font-medium text-white">
          So'nggi vazifalar
          {loading && tasks.length === 0 && (
            <span className="ml-2 text-xs text-slate-500">Yuklanmoqda…</span>
          )}
        </h2>
        <ul className="space-y-2">
          {tasks.map((t) => (
            <li key={t.id}>
              <Link
                to={`/tasks/${t.id}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 transition hover:border-slate-600 hover:bg-slate-800/50"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 truncate">{t.command_text}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    #{t.id} · {new Date(t.created_at).toLocaleString("uz-UZ")}
                    {t.server_id && servers.find((s) => s.id === t.server_id) && (
                      <span className="ml-2 text-slate-600">
                        · {servers.find((s) => s.id === t.server_id)?.name}
                      </span>
                    )}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    STATUS_BADGE[t.status] || "bg-slate-700 text-slate-300"
                  }`}
                >
                  {STATUS_LABEL[t.status] || t.status}
                </span>
              </Link>
            </li>
          ))}
          {tasks.length === 0 && !loading && (
            <p className="text-center text-slate-500 py-8">Hali vazifa yo'q. Yuqorida buyruq yuboring.</p>
          )}
        </ul>
      </div>
    </div>
  );
}
