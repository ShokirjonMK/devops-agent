import { useEffect, useState } from "react";
import { api } from "../../api";

export default function AdminSettings() {
  const [rows, setRows] = useState<
    { key: string; value: unknown; description: string | null; updated_at: string | null }[]
  >([]);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);

  const load = () =>
    api.adminSettings().then(setRows).catch((e: Error) => setErr(e.message));

  useEffect(() => {
    load();
  }, []);

  const save = async (key: string) => {
    setErr(null);
    const raw = (edit[key] ?? "").trim();
    let val: unknown = raw;
    try {
      val = JSON.parse(raw);
    } catch {
      /* matn */
    }
    try {
      await api.adminPatchSetting(key, val);
      setEdit((e) => {
        const n = { ...e };
        delete n[key];
        return n;
      });
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (err && rows.length === 0) {
    return <p className="text-rose-400">{err}</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Admin · Global sozlamalar</h1>
      {err && <p className="text-sm text-rose-400">{err}</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 bg-slate-900/80 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Kalit</th>
              <th className="px-4 py-2">Qiymat (JSON)</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-b border-slate-800/80">
                <td className="px-4 py-2 font-mono text-xs text-emerald-300/90">{r.key}</td>
                <td className="px-4 py-2">
                  <textarea
                    className="min-h-[4rem] w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-xs"
                    defaultValue={JSON.stringify(r.value)}
                    onChange={(e) => setEdit((x) => ({ ...x, [r.key]: e.target.value }))}
                  />
                  {r.description && <p className="mt-1 text-xs text-slate-500">{r.description}</p>}
                </td>
                <td className="px-4 py-2">
                  <button
                    type="button"
                    onClick={() => save(r.key)}
                    className="rounded bg-emerald-600 px-3 py-1 text-xs text-white hover:bg-emerald-500"
                  >
                    Saqlash
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
