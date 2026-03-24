import { useEffect, useState } from "react";
import { api, getStoredToken, setStoredToken, type AiKeyMeta } from "../api";

export default function AiKeys() {
  const [token, setToken] = useState(() => getStoredToken() || "");
  const [keys, setKeys] = useState<AiKeyMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [name, setName] = useState("default");
  const [provider, setProvider] = useState<"openai" | "anthropic">("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [saving, setSaving] = useState(false);

  const saveSession = () => {
    const t = token.trim();
    setStoredToken(t || null);
    setErr(null);
    loadKeys();
  };

  const loadKeys = () => {
    if (!getStoredToken()) {
      setKeys([]);
      return;
    }
    setLoading(true);
    api
      .listAiKeys()
      .then(setKeys)
      .catch((e: Error) => {
        setErr(e.message);
        setKeys([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (getStoredToken()) loadKeys();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!getStoredToken()) {
      setErr("Avval JWT ni saqlang (Telegram /auth/telegram dan).");
      return;
    }
    if (!apiKey.trim()) return;
    setSaving(true);
    setErr(null);
    try {
      await api.createAiKey({
        name: name.trim() || "default",
        provider,
        api_key: apiKey.trim(),
        base_url: baseUrl.trim() || null,
        model: model.trim() || null,
      });
      setApiKey("");
      loadKeys();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Kalitni o‘chirish?")) return;
    setErr(null);
    try {
      await api.deleteAiKey(id);
      loadKeys();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">AI kalitlar</h1>
        <p className="mt-1 text-slate-400">
          Har bir foydalanuvchi o‘z kalitlarini shifrlangan saqlaydi. Vazifa yaratishda JWT yuborilsa yoki Telegram
          orqali kelgan bo‘lsa, agent shu kalitlardan foydalanadi (aks holda server .env).
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-lg font-medium text-white">Sessiya (JWT)</h2>
        <p className="mt-1 text-sm text-slate-500">
          Telegram Login orqali olingan tokenni qo‘ying (POST /api/auth/telegram). Brauzerda barcha so‘rovlarga
          avtomatik qo‘shiladi.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <input
            type="password"
            autoComplete="off"
            className="min-w-[240px] flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100"
            placeholder="access_token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button
            type="button"
            onClick={saveSession}
            className="rounded-lg bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600"
          >
            Saqlash
          </button>
          <button
            type="button"
            onClick={() => {
              setToken("");
              setStoredToken(null);
              setKeys([]);
            }}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            Tozalash
          </button>
        </div>
      </div>

      <form
        onSubmit={submit}
        className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5"
      >
        <h2 className="text-lg font-medium text-white">Yangi kalit</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs text-slate-500">Nom</label>
            <input
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-slate-500">Provayder</label>
            <select
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
              value={provider}
              onChange={(e) => setProvider(e.target.value as "openai" | "anthropic")}
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500">API kalit</label>
          <input
            type="password"
            autoComplete="off"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs text-slate-500">Base URL (ixtiyoriy)</label>
            <input
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              placeholder="https://api.openai.com/v1"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-slate-500">Model (ixtiyoriy)</label>
            <input
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              placeholder="gpt-4o-mini / claude-3-5-sonnet-..."
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {saving ? "Saqlanmoqda…" : "Qo‘shish"}
        </button>
      </form>

      {err && <p className="text-sm text-rose-400">{err}</p>}

      <div>
        <h2 className="mb-3 text-lg font-medium text-white">Ro‘yxat</h2>
        {loading ? (
          <p className="text-slate-500">Yuklanmoqda…</p>
        ) : keys.length === 0 ? (
          <p className="text-slate-500">
            {getStoredToken() ? "Hali kalit yo‘q." : "JWT saqlang va yangilang."}
          </p>
        ) : (
          <ul className="space-y-2">
            {keys.map((k) => (
              <li
                key={k.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
              >
                <div>
                  <p className="text-sm text-slate-200">
                    <span className="font-medium">{k.name}</span>{" "}
                    <span className="text-slate-500">· {k.provider}</span>
                  </p>
                  <p className="text-xs text-slate-500">{k.created_at && new Date(k.created_at).toLocaleString()}</p>
                </div>
                <button
                  type="button"
                  onClick={() => remove(k.id)}
                  className="rounded-lg border border-rose-900/50 px-3 py-1 text-xs text-rose-300 hover:bg-rose-950/40"
                >
                  O‘chirish
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
