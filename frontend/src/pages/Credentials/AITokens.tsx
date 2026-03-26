import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";

type TokenRow = {
  id: string;
  provider: string;
  name: string;
  model_override?: string | null;
  base_url?: string | null;
  is_default: boolean;
  is_active: boolean;
  usage_this_month_usd: string;
  monthly_budget_usd?: string | null;
  last_used_at?: string | null;
};

export default function AITokensPage() {
  const [rows, setRows] = useState<TokenRow[]>([]);
  const [providers, setProviders] = useState<Record<string, { base_url: string | null; models: string[] }>>({});
  const [err, setErr] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("openai");
  const [token, setToken] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [modelOverride, setModelOverride] = useState("");
  const [budget, setBudget] = useState("");
  const [testing, setTesting] = useState<string | null>(null);
  const [modal, setModal] = useState(false);

  const grouped = useMemo(() => {
    const m = new Map<string, TokenRow[]>();
    for (const r of rows) {
      const k = r.provider;
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(r);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [rows]);

  const load = () => {
    api
      .listAiTokens()
      .then((r) => setRows(r as TokenRow[]))
      .catch((e: Error) => setErr(e.message));
    api.listAiTokenProviders().then(setProviders).catch(() => {});
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
        base_url: baseUrl.trim() || null,
        model_override: modelOverride.trim() || null,
        monthly_budget_usd: budget.trim() || null,
        is_default: true,
      });
      setToken("");
      setName("");
      setBaseUrl("");
      setModelOverride("");
      setBudget("");
      setModal(false);
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

  const setDefault = async (id: string) => {
    try {
      await api.patchAiToken(id, { is_default: true });
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const usageBar = (r: TokenRow) => {
    const used = parseFloat(r.usage_this_month_usd || "0") || 0;
    const cap = r.monthly_budget_usd ? parseFloat(r.monthly_budget_usd) : null;
    const pct = cap && cap > 0 ? Math.min(100, (used / cap) * 100) : 0;
    return (
      <div className="mt-2 space-y-1">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Usage</span>
          <span>
            ${used.toFixed(4)}
            {cap != null && cap > 0 ? ` / $${cap.toFixed(2)}` : ""}
          </span>
        </div>
        {cap != null && cap > 0 ? (
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-violet-500/80" style={{ width: `${pct}%` }} />
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">AI tokenlar</h1>
          <p className="mt-1 text-slate-400">
            Qiymat javobda qaytmaydi — faqat ●●●●xxxx mask va meta. Provayder bo‘yicha guruhlangan.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setModal(true)}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        >
          Qo‘shish
        </button>
      </div>

      {err && <p className="rounded-lg border border-rose-900/40 bg-rose-950/30 p-3 text-sm text-rose-300">{err}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        {grouped.map(([prov, items]) => (
          <section key={prov} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{prov}</h2>
            <ul className="mt-3 space-y-3">
              {items.map((r) => (
                <li key={r.id} className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-white">{r.name}</p>
                      <p className="text-xs text-slate-500">●●●● (token ko‘rinmaydi)</p>
                      {r.is_default && (
                        <span className="mt-1 inline-block rounded bg-amber-500/20 px-2 py-0.5 text-[10px] text-amber-200">
                          default
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="text-xs text-sky-400 hover:underline"
                        onClick={() => test(r.id)}
                        disabled={testing === r.id}
                      >
                        {testing === r.id ? "Test…" : "Test"}
                      </button>
                      <button type="button" className="text-xs text-amber-400 hover:underline" onClick={() => setDefault(r.id)}>
                        Default
                      </button>
                      <button type="button" className="text-xs text-rose-400 hover:underline" onClick={() => del(r.id)}>
                        O‘chirish
                      </button>
                    </div>
                  </div>
                  {usageBar(r)}
                </li>
              ))}
            </ul>
          </section>
        ))}
        {rows.length === 0 && <p className="text-slate-500">Hali token yo‘q.</p>}
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form
            onSubmit={add}
            className="w-full max-w-lg space-y-3 rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl"
          >
            <h3 className="text-lg font-medium text-white">Yangi token</h3>
            <select
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {Object.keys(providers)
                .sort()
                .map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
            </select>
            <input
              required
              placeholder="Nom"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              type="password"
              required
              placeholder="Token (sk-...)"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
            <input
              placeholder="Base URL (custom uchun)"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
            <input
              placeholder="Model override"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={modelOverride}
              onChange={(e) => setModelOverride(e.target.value)}
            />
            <input
              placeholder="Oy byudjeti USD (ixtiyoriy)"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="rounded-lg px-4 py-2 text-sm text-slate-400" onClick={() => setModal(false)}>
                Bekor
              </button>
              <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white">
                Saqlash
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
