import { useEffect, useState } from "react";
import { api } from "../api";

type Plan = {
  id: string;
  name: string;
  price_usd: number;
  price_uzs: number;
  billing_period: string;
  limits: Record<string, number | boolean | string>;
  features_list: string[];
  is_public: boolean;
};

export default function Upgrade() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [currency, setCurrency] = useState<"usd" | "uzs">("usd");
  const [provider, setProvider] = useState<"stripe" | "click" | "payme">("click");
  const [checkingOut, setCheckingOut] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listPlans().then(setPlans).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function handleCheckout(planId: string) {
    setCheckingOut(planId);
    setError(null);
    try {
      let url: string;
      if (provider === "stripe") {
        const r = await api.checkoutStripe(planId);
        url = r.checkout_url;
      } else if (provider === "click") {
        const r = await api.checkoutClick(planId);
        url = r.payment_url;
      } else {
        const r = await api.checkoutPayme(planId);
        url = r.payment_url;
      }
      window.location.href = url;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCheckingOut(null);
    }
  }

  const publicPlans = plans.filter((p) => p.is_public);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Tarif Tanlang</h1>
        <p className="text-slate-400">Loyihangizga mos rejimni tanlang</p>
      </div>

      {/* Currency + Provider toggle */}
      <div className="flex flex-wrap gap-4 justify-center mb-8">
        <div className="flex rounded-lg overflow-hidden border border-slate-700">
          <button
            onClick={() => setCurrency("usd")}
            className={`px-4 py-2 text-sm font-medium transition ${currency === "usd" ? "bg-emerald-500 text-white" : "bg-slate-800 text-slate-400 hover:text-white"}`}
          >
            USD ($)
          </button>
          <button
            onClick={() => setCurrency("uzs")}
            className={`px-4 py-2 text-sm font-medium transition ${currency === "uzs" ? "bg-emerald-500 text-white" : "bg-slate-800 text-slate-400 hover:text-white"}`}
          >
            UZS (so'm)
          </button>
        </div>
        <div className="flex rounded-lg overflow-hidden border border-slate-700">
          {(["click", "payme", "stripe"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setProvider(p)}
              className={`px-4 py-2 text-sm font-medium transition capitalize ${provider === p ? "bg-blue-500 text-white" : "bg-slate-800 text-slate-400 hover:text-white"}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-500/20 border border-red-500/40 px-4 py-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center text-slate-500 py-16">Yuklanmoqda…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {publicPlans.map((plan) => {
            const isFree = plan.id === "free";
            const price = currency === "usd"
              ? `$${plan.price_usd}/oy`
              : plan.price_uzs
              ? `${plan.price_uzs.toLocaleString()} so'm/oy`
              : "Bepul";
            return (
              <div
                key={plan.id}
                className={`rounded-xl border p-6 flex flex-col gap-4 ${
                  plan.id === "pro"
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-slate-700 bg-slate-800/50"
                }`}
              >
                {plan.id === "pro" && (
                  <div className="text-xs font-bold text-emerald-400 uppercase tracking-widest">
                    Mashhur
                  </div>
                )}
                <div>
                  <div className="text-lg font-bold text-white">{plan.name}</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{price}</div>
                </div>
                <ul className="flex-1 space-y-1.5">
                  {(plan.features_list || []).map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="text-emerald-400 mt-0.5">✓</span>
                      {f}
                    </li>
                  ))}
                  {plan.limits.tasks_per_month && (
                    <li className="text-xs text-slate-500 mt-2">
                      {plan.limits.tasks_per_month === -1
                        ? "Cheksiz vazifalar"
                        : `${plan.limits.tasks_per_month} vazifa/oy`}
                    </li>
                  )}
                </ul>
                {!isFree && (
                  <button
                    onClick={() => handleCheckout(plan.id)}
                    disabled={checkingOut === plan.id}
                    className={`w-full py-2.5 rounded-lg text-sm font-semibold transition ${
                      plan.id === "pro"
                        ? "bg-emerald-500 hover:bg-emerald-400 text-white"
                        : "bg-slate-700 hover:bg-slate-600 text-white"
                    } disabled:opacity-50`}
                  >
                    {checkingOut === plan.id ? "Yo'naltirilmoqda…" : "Tanlash"}
                  </button>
                )}
                {isFree && (
                  <div className="text-center text-sm text-slate-500">Joriy rejim</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
