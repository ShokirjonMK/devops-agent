import { useEffect, useState } from "react";
import { api } from "../../api";

type Row = {
  id: string;
  actor_user_id: string | null;
  action_type: string;
  resource_type: string | null;
  resource_id: string | null;
  created_at: string | null;
};

export default function AdminAudit() {
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [action, setAction] = useState("");

  const load = () => {
    const q = action.trim() ? `?action=${encodeURIComponent(action.trim())}` : "";
    api
      .adminAuditLogs(q)
      .then((r) => setRows(r as Row[]))
      .catch((e: Error) => setErr(e.message));
  };

  useEffect(() => {
    load();
  }, []);

  const exportCsv = async () => {
    try {
      const text = await api.adminAuditExportCsv();
      const blob = new Blob([text], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "audit.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (err && rows.length === 0) return <p className="text-rose-400">{err}</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        <h1 className="text-2xl font-semibold text-white">Admin · Audit</h1>
        <input
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm"
          placeholder="action_type filter"
          value={action}
          onChange={(e) => setAction(e.target.value)}
        />
        <button type="button" onClick={load} className="rounded-lg bg-slate-700 px-3 py-1.5 text-sm text-white">
          Filtrlash
        </button>
        <button type="button" onClick={exportCsv} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm text-white">
          CSV eksport
        </button>
      </div>
      {err && <p className="text-sm text-rose-400">{err}</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-500">
            <tr>
              <th className="px-3 py-2">Vaqt</th>
              <th className="px-3 py-2">Actor</th>
              <th className="px-3 py-2">Action</th>
              <th className="px-3 py-2">Resource</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-800/60">
                <td className="px-3 py-2 font-mono text-slate-500">{r.created_at}</td>
                <td className="px-3 py-2 font-mono">{r.actor_user_id ?? "—"}</td>
                <td className="px-3 py-2">{r.action_type}</td>
                <td className="px-3 py-2">
                  {r.resource_type}:{r.resource_id}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
