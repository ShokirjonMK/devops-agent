import { useEffect, useState } from "react";
import { api } from "../api";

export default function AITokens() {
  const [rows, setRows] = useState<
    {
      id: string;
      provider: string;
      name: string;
      is_default: boolean;
      is_active: boolean;
      usage_this_month_usd: string;
    }[]
  >([]);
  const [providers, setProviders] = useState<Record<string, { base_url: string | null; models: string[] }>>({});
  const [err, setErr] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("openai");
  const [token, setToken] = useState("");
  const [testing, setTesting] = useState<string | null>(null);

  const load = () => {
    api
      .listAiTokens()
      .then(setRows)
      .catch((e: Error) => setErr(e.message));
    api
      .listAiTokenProviders()
      .then(setProviders)
      .catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api.createAiToken({
        provider,
        name: name.trim() || "default",
        token_value: token.trim(),
        is_default: true,
      });
      setToken("");
      setName("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const test = async (id: string) => {
    setTesting(id);
    setErr(null);
    try {
      const r = await api.testAiToken(id);
      alert(r.success ? `OK ${r.latency_ms}ms · ${r.model_used}` : `Xato: ${r.detail}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setTesting(null);
    }
  };

  const del = async (id: string) => {
    if (!confirm("O‘chirilsinmi?")) return;
    try {
      await api.deleteAiToken(id);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">AI tokenlar (multi-provider)</h1>
        <p className="mt-1 text-slate-400">
          Token qiymati javobda qaytmaydi. JWT va operator roli kerak. Provayderlar:{" "}
          {Object.keys(providers).join(", ") || "…"}
        </p>
      </div>

      <form
        onSubmit={add}
        className="max-w-xl space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5"
      >
        <h2 className="text-lg font-medium text-white">Yangi token</h2>
        <div>
          <label className="text-xs text-slate-500">Provayder</label>
          <select
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            {Object.keys(providers).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Nom</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="masalan: ish-ofis"
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">API kalit</label>
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoComplete="off"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        >
          Saqlash
        </button>
        {err && <p className="text-sm text-rose-400">{err}</p>}
      </form>

      <div>
        <h2 className="mb-3 text-lg font-medium text-white">Ro‘yxat</h2>
        <ul className="space-y-2">
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
            >
              <div>
                <p className="font-medium text-white">
                  {r.provider} / {r.name}
                  {r.is_default && (
                    <span className="ml-2 rounded bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-300">
                      default
                    </span>
                  )}
                </p>
                <p className="text-xs text-slate-500">
                  ishlatilgan: {r.usage_this_month_usd} USD · faol: {String(r.is_active)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => test(r.id)}
                  disabled={testing === r.id}
                  className="rounded border border-slate-600 px-3 py-1 text-xs text-slate-200 hover:bg-slate-800"
                >
                  {testing === r.id ? "…" : "Test"}
                </button>
                <button
                  type="button"
                  onClick={() => del(r.id)}
                  className="rounded border border-rose-900/50 px-3 py-1 text-xs text-rose-300 hover:bg-rose-950/40"
                >
                  O‘chirish
                </button>
              </div>
            </li>
          ))}
          {rows.length === 0 && <p className="text-slate-500">Hozircha yo‘q.</p>}
        </ul>
      </div>
    </div>
  );
}
