import { useEffect, useState } from "react";
import { api } from "../../api";

export default function AdminAIProviders() {
  const [rows, setRows] = useState<{ provider: string; model: string; key_hint: string }[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");

  const load = () =>
    api.adminSystemAi().then(setRows).catch((e: Error) => setErr(e.message));

  useEffect(() => {
    load();
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api.adminUpsertSystemAi({ provider, api_key: apiKey, model });
      setApiKey("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (err && rows.length === 0) return <p className="text-rose-400">{err}</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-white">Admin · Tizim AI (fallback)</h1>
      {err && <p className="text-sm text-rose-400">{err}</p>}
      <form onSubmit={save} className="max-w-xl space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
        <input
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          placeholder="API kalit"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
        <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white">
          Saqlash (masklangan ko‘rinish)
        </button>
      </form>
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.provider} className="rounded-lg border border-slate-800 bg-slate-950/40 px-4 py-3 text-sm">
            <span className="font-medium text-white">{r.provider}</span> · {r.model} ·{" "}
            <span className="text-slate-400">{r.key_hint}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
