import { useEffect, useState } from "react";
import { api, type AiKeyMeta } from "../api";

// Recommended models per provider
const MODELS = {
  anthropic: [
    {
      value: "claude-sonnet-4-20250514",
      label: "Claude Sonnet 4 (20250514) — eng barqaror, tavsiya",
    },
    { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6 (eng yangi alias)" },
    { value: "claude-sonnet-4-5-20250929", label: "Claude Sonnet 4.5 (snapshot)" },
    { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (tez, arzon)" },
    { value: "claude-3-5-sonnet-20241022", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-haiku-20240307", label: "Claude 3 Haiku" },
  ],
  openai: [
    { value: "gpt-4o", label: "GPT-4o (tavsiya etiladi)" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini (tez, arzon)" },
    { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
    { value: "o3-mini", label: "o3-mini (mulohazali)" },
  ],
};

const PROVIDER_INFO = {
  anthropic: {
    name: "Anthropic (Claude)",
    color: "from-orange-500/20 to-orange-500/5 border-orange-500/30",
    badge: "bg-orange-500/20 text-orange-300",
    keyPrefix: "sk-ant-",
    keyExample: "sk-ant-api03-... yoki sk-ant-api04-...",
    steps: [
      {
        text: "⚠️ claude.ai obunasi (Plus/Pro) API kalit bermaydi — bu alohida hisob. Ro’yxatdan o’ting yoki kiring:",
        link: "https://platform.claude.com",
      },
      {
        text: "Chap menyu → API Keys (yoki to’g’ridan-to’g’ri):",
        link: "https://platform.claude.com/settings/keys",
      },
      {
        text: "Workspace kaliti uchun (agar workspace ishlatsangiz):",
        link: "https://platform.claude.com/settings/workspaces/default/keys",
      },
      { text: "«Create Key» tugmasini bosing → nom bering → kalitni KO’CHIRIB OLING (faqat bir marta ko’rsatiladi)." },
      { text: "Quyidagi formada: Anthropic tanlang, kalitni joylashtiring, model = «Claude Sonnet 4 (20250514)», saqlang." },
    ],
  },
  openai: {
    name: "OpenAI (GPT)",
    color: "from-emerald-500/20 to-emerald-500/5 border-emerald-500/30",
    badge: "bg-emerald-500/20 text-emerald-300",
    keyPrefix: "sk-",
    keyExample: "sk-proj-... yoki sk-...",
    steps: [
      { text: "⚠️ ChatGPT Plus obunasi API kalit bermaydi — bu alohida hisob. Kiring yoki ro’yxatdan o’ting:", link: "https://platform.openai.com" },
      { text: "Chap menyu → API keys → «Create new secret key»." },
      { text: "Nom bering → «Create» → kalitni KO’CHIRIB OLING (faqat bir marta ko’rsatiladi)." },
      { text: "Billing → Payment method qo’shing (API bepul emas; $5-10 kredit yetarli)." },
      { text: "Quyidagi formada: OpenAI tanlang, kalitni joylashtiring, saqlang." },
    ],
  },
};

export default function AiKeys() {
  const [keys, setKeys] = useState<AiKeyMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [provider, setProvider] = useState<"anthropic" | "openai">("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("claude-sonnet-4-20250514");
  const [name, setName] = useState("default");
  const [saving, setSaving] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [activeGuide, setActiveGuide] = useState<"anthropic" | "openai" | null>(null);

  const loadKeys = () => {
    setLoading(true);
    api
      .listAiKeys()
      .then(setKeys)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadKeys(); }, []);

  const handleProviderChange = (p: "anthropic" | "openai") => {
    setProvider(p);
    setModel(MODELS[p][0].value);
    setApiKey("");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setSaving(true);
    setErr(null);
    setSuccess(null);
    try {
      await api.createAiKey({
        name: name.trim() || "default",
        provider,
        api_key: apiKey.trim(),
        model: model || null,
      });
      setApiKey("");
      setSuccess(`✓ ${provider === "anthropic" ? "Anthropic" : "OpenAI"} kaliti muvaffaqiyatli qo'shildi!`);
      loadKeys();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("allaqachon bor")) {
        setErr("Bu nom bilan kalit allaqachon mavjud. Avval o'chirib qayta qo'shing.");
      } else {
        setErr(msg);
      }
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string, providerName: string) => {
    if (!confirm(`"${providerName}" kalitini o'chirishni tasdiqlaysizmi?`)) return;
    setErr(null);
    try {
      await api.deleteAiKey(id);
      setSuccess("Kalit o'chirildi.");
      loadKeys();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const info = PROVIDER_INFO[provider];

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">AI Kalitlar</h1>
        <p className="mt-1 text-slate-400">
          Vazifalarni bajarishda agent sizning shaxsiy AI kalitingizdan foydalanadi.
          Kalit shifrlangan holda saqlanadi.
        </p>
      </div>

      {/* How it works */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-sm text-slate-300">
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div className="space-y-3">
            <div>
              <div className="font-medium text-white mb-1">Qanday ishlaydi?</div>
              <ul className="space-y-1 text-slate-400">
                <li>1. Pastdagi «qo‘llanma»dan Claude yoki OpenAI uchun API kalit oling.</li>
                <li>2. Kalitni shu sahifada saqlang — u serverda shifrlanadi.</li>
                <li>3. Vazifa yuborganingizda agent aynan shu kalit bilan LLM ga murojaat qiladi.</li>
                <li>4. Faqat bitta provayder kaliti bo‘lsa, u avtomatik tanlanadi; ikkalasi bo‘lsa — serverdagi AI_PROVIDER qoidasiga qarab.</li>
              </ul>
            </div>
            <div className="rounded-lg border border-slate-600/50 bg-slate-900/40 p-3 text-xs text-slate-400">
              <div className="font-medium text-slate-300 mb-1">404 yoki «Not Found» (Anthropic)</div>
              <p>
                Bu odatda model nomi hisobingizda yo‘q degani. Kalitni o‘chirib qayta qo‘shing va model sifatida
                «Claude Sonnet 4 (20250514)» ni tanlang. Kalit to‘g‘ri bo‘lsa, server ketma-ket boshqa modellarni ham
                sinab ko‘radi.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Provider selector */}
      <div className="flex rounded-xl overflow-hidden border border-slate-700">
        {(["anthropic", "openai"] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => handleProviderChange(p)}
            className={`flex-1 py-3 px-4 text-sm font-medium transition flex items-center justify-center gap-2 ${
              provider === p
                ? "bg-slate-700 text-white"
                : "bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800"
            }`}
          >
            {p === "anthropic" ? "🟠 Anthropic (Claude)" : "🟢 OpenAI (GPT)"}
          </button>
        ))}
      </div>

      {/* Guide toggle */}
      <button
        type="button"
        onClick={() => setActiveGuide(activeGuide === provider ? null : provider)}
        className="w-full flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/40 px-4 py-3 text-sm text-slate-300 hover:border-slate-600 transition"
      >
        <span>
          📖 {provider === "anthropic" ? "Anthropic" : "OpenAI"} kalitini qanday olish kerak?
        </span>
        <span className="text-slate-500">{activeGuide === provider ? "▲ Yopish" : "▼ Ko'rsatish"}</span>
      </button>

      {activeGuide === provider && (
        <div className={`rounded-xl border bg-gradient-to-br p-5 ${info.color}`}>
          <h3 className="font-semibold text-white mb-3">
            {provider === "anthropic" ? "🟠 Anthropic API kaliti olish" : "🟢 OpenAI API kaliti olish"}
          </h3>
          <ol className="space-y-2">
            {info.steps.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="text-slate-500 font-mono text-xs mt-0.5 shrink-0">{i + 1}.</span>
                <span>
                  {s.link ? (
                    <>
                      {s.text}{" "}
                      <a
                        href={s.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald-400 underline hover:text-emerald-300 break-all"
                      >
                        {s.link.replace("https://", "")}
                      </a>
                    </>
                  ) : (
                    s.text
                  )}
                </span>
              </li>
            ))}
          </ol>
          <div className="mt-3 rounded-lg bg-black/20 px-3 py-2 text-xs text-slate-400 font-mono">
            Kalit ko'rinishi: {info.keyExample}
          </div>
          {provider === "anthropic" && (
            <div className="mt-2 text-xs text-slate-500">
              💰 Yangi Anthropic akkauntlarga $5 bepul kredit beriladi
            </div>
          )}
          {provider === "openai" && (
            <div className="mt-2 text-xs text-slate-500">
              💰 Yangi OpenAI akkauntlarga $5-18 bepul kredit beriladi
            </div>
          )}
        </div>
      )}

      {/* Add key form */}
      <form onSubmit={submit} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
        <h2 className="text-base font-medium text-white">
          {provider === "anthropic" ? "🟠 Anthropic kaliti qo'shish" : "🟢 OpenAI kaliti qo'shish"}
        </h2>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            API Kalit <span className="text-rose-400">*</span>
          </label>
          <div className="relative">
            <input
              type={showKey ? "text" : "password"}
              autoComplete="off"
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none pr-20"
              placeholder={info.keyExample}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300 px-2 py-1"
            >
              {showKey ? "yashir" : "ko'rsat"}
            </button>
          </div>
          {apiKey && !apiKey.startsWith(info.keyPrefix) && (
            <p className="mt-1 text-xs text-yellow-400">
              ⚠️ Kalit <code>{info.keyPrefix}...</code> bilan boshlanishi kerak
            </p>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Model</label>
          <select
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-500 focus:outline-none"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {MODELS[provider].map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Kalit nomi (bir nechta kalit bo'lsa)
          </label>
          <input
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
            placeholder="default"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <button
          type="submit"
          disabled={saving || !apiKey.trim()}
          className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 transition"
        >
          {saving ? "Saqlanmoqda…" : `${provider === "anthropic" ? "Anthropic" : "OpenAI"} kalitini saqlash`}
        </button>
      </form>

      {err && (
        <div className="rounded-lg border border-rose-900/50 bg-rose-950/40 p-3 text-sm text-rose-300">
          {err}
        </div>
      )}
      {success && (
        <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/40 p-3 text-sm text-emerald-300">
          {success}
        </div>
      )}

      {/* Keys list */}
      <div>
        <h2 className="mb-3 text-base font-medium text-white">
          Saqlangan kalitlar
          {keys.length > 0 && (
            <span className="ml-2 rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-400">
              {keys.length}
            </span>
          )}
        </h2>
        {loading ? (
          <p className="text-slate-500 text-sm">Yuklanmoqda…</p>
        ) : keys.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-6 text-center text-slate-500 text-sm">
            Hali kalit qo'shilmagan.<br />
            <span className="text-xs">Yuqoridagi forma orqali birinchi kalitingizni qo'shing.</span>
          </div>
        ) : (
          <ul className="space-y-2">
            {keys.map((k) => {
              const provInfo = PROVIDER_INFO[k.provider as keyof typeof PROVIDER_INFO];
              return (
                <li
                  key={k.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{k.provider === "anthropic" ? "🟠" : "🟢"}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{k.name}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs ${provInfo?.badge || "bg-slate-700 text-slate-300"}`}>
                          {k.provider}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {k.created_at && `Qo'shilgan: ${new Date(k.created_at).toLocaleString("uz-UZ")}`}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => remove(k.id, `${k.name} (${k.provider})`)}
                    className="shrink-0 rounded-lg border border-rose-900/50 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-950/40 transition"
                  >
                    O'chirish
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Note about AI Tokens */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/20 p-4 text-xs text-slate-500">
        <strong className="text-slate-400">Eslatma:</strong> Bu sahifada saqlangan kalitlar agent vazifalarida
        ishlatiladi. Maxsus model sozlamalari uchun{" "}
        <a href="/credentials/tokens" className="text-emerald-400 underline">
          AI Tokens sahifasini
        </a>{" "}
        ham ko'ring.
      </div>
    </div>
  );
}
