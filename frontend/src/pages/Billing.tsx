import { useEffect, useState } from "react";
import { api } from "../api";

type Subscription = {
  plan_name: string;
  price_usd: number;
  tasks_used_month: number;
  tasks_limit: number;
  servers_used: number;
  servers_limit: number;
  period_end?: string;
  trial_ends_at?: string | null;
  ai_credit_balance_usd: number;
};

type Invoice = {
  id: string;
  plan_id: string;
  provider: string;
  amount_usd: number;
  amount_local: number | null;
  currency_local: string | null;
  status: string;
  created_at: string | null;
  paid_at: string | null;
};

type CreditTx = {
  id: string;
  type: string;
  amount_usd: number;
  description: string | null;
  provider: string | null;
  tokens_used: number | null;
  created_at: string | null;
};

type CreditData = {
  balance_usd: number;
  total_deposited_usd: number;
  total_spent_usd: number;
  transactions: CreditTx[];
};

type CreditPackage = {
  id: string;
  amount_usd: number;
  label: string;
  price_uzs: number;
};

function ProgressBar({ used, limit }: { used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const color = pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-yellow-500" : "bg-emerald-500";
  return (
    <div className="mt-1">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{used} / {limit === -1 ? "∞" : limit}</span>
        <span>{limit === -1 ? "∞" : pct + "%"}</span>
      </div>
      {limit > 0 && (
        <div className="h-1.5 rounded-full bg-slate-700">
          <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

export default function Billing() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [credits, setCredits] = useState<CreditData | null>(null);
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [buyingPkg, setBuyingPkg] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getSubscription().then(setSub),
      api.listInvoices().then(setInvoices),
      api.getCredits().then(setCredits),
      api.listCreditPackages().then(setPackages),
    ])
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleCancelSubscription() {
    if (!confirm("Obunani bekor qilishni tasdiqlaysizmi?")) return;
    setCancelling(true);
    try {
      await api.cancelSubscription();
      const updated = await api.getSubscription();
      setSub(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCancelling(false);
    }
  }

  async function handleBuyCredit(pkgId: string) {
    setBuyingPkg(pkgId);
    setError(null);
    try {
      const r = await api.checkoutCredit(pkgId, "click");
      window.location.href = r.payment_url;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBuyingPkg(null);
    }
  }

  if (loading) {
    return <div className="text-center text-slate-500 py-16">Yuklanmoqda…</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Billing</h1>

      {error && (
        <div className="rounded-lg bg-red-500/20 border border-red-500/40 px-4 py-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Subscription */}
      {sub && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="text-sm text-slate-400 mb-1">Joriy tarif</div>
              <div className="text-xl font-bold text-white">{sub.plan_name}</div>
              {sub.price_usd > 0 && (
                <div className="text-sm text-slate-400 mt-0.5">${sub.price_usd}/oy</div>
              )}
              {sub.trial_ends_at && (
                <div className="text-xs text-yellow-400 mt-1">
                  Trial: {new Date(sub.trial_ends_at).toLocaleDateString("uz-UZ")} gacha
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <a
                href="/upgrade"
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-medium transition"
              >
                Yangilash
              </a>
              {sub.price_usd > 0 && (
                <button
                  onClick={handleCancelSubscription}
                  disabled={cancelling}
                  className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-red-500/20 text-slate-300 hover:text-red-400 text-sm font-medium transition disabled:opacity-50"
                >
                  {cancelling ? "…" : "Bekor qilish"}
                </button>
              )}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-slate-400">Vazifalar (oy)</div>
              <ProgressBar used={sub.tasks_used_month} limit={sub.tasks_limit} />
            </div>
            <div>
              <div className="text-sm text-slate-400">Serverlar</div>
              <ProgressBar used={sub.servers_used} limit={sub.servers_limit} />
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-700 flex items-center justify-between">
            <div className="text-sm text-slate-400">AI Kredit Balans</div>
            <div className="text-lg font-semibold text-emerald-400">
              ${sub.ai_credit_balance_usd.toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {/* AI Credit packages */}
      {packages.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">AI Kredit To'ldirish</h2>
          <div className="grid grid-cols-3 gap-3">
            {packages.map((pkg) => (
              <button
                key={pkg.id}
                onClick={() => handleBuyCredit(pkg.id)}
                disabled={buyingPkg === pkg.id}
                className="rounded-lg border border-slate-600 bg-slate-700/50 p-4 text-left hover:border-emerald-500 transition disabled:opacity-50"
              >
                <div className="text-lg font-bold text-emerald-400">{pkg.label}</div>
                <div className="text-sm text-slate-400 mt-0.5">
                  {pkg.price_uzs ? `${pkg.price_uzs.toLocaleString()} so'm` : `$${pkg.amount_usd}`}
                </div>
                {buyingPkg === pkg.id && (
                  <div className="text-xs text-slate-500 mt-1">Yo'naltirilmoqda…</div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Credit transactions */}
      {credits && credits.transactions.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Kredit Tarixi</h2>
          <div className="space-y-2">
            {credits.transactions.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                <div>
                  <div className="text-sm text-white">{tx.description || tx.type}</div>
                  <div className="text-xs text-slate-500">
                    {tx.created_at ? new Date(tx.created_at).toLocaleDateString("uz-UZ") : ""}
                    {tx.provider && ` · ${tx.provider}`}
                    {tx.tokens_used && ` · ${tx.tokens_used.toLocaleString()} token`}
                  </div>
                </div>
                <div className={`text-sm font-medium ${tx.type === "debit" ? "text-red-400" : "text-emerald-400"}`}>
                  {tx.type === "debit" ? "-" : "+"}${Math.abs(tx.amount_usd).toFixed(4)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invoices */}
      {invoices.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">To'lovlar Tarixi</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left pb-2 font-medium">Sana</th>
                  <th className="text-left pb-2 font-medium">Tarif</th>
                  <th className="text-left pb-2 font-medium">Provider</th>
                  <th className="text-right pb-2 font-medium">Summa</th>
                  <th className="text-right pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-slate-700/50 last:border-0">
                    <td className="py-2 text-slate-300">
                      {inv.paid_at ? new Date(inv.paid_at).toLocaleDateString("uz-UZ") : "—"}
                    </td>
                    <td className="py-2 text-slate-300">{inv.plan_id}</td>
                    <td className="py-2 text-slate-400 capitalize">{inv.provider}</td>
                    <td className="py-2 text-right text-white">
                      {inv.amount_local
                        ? `${inv.amount_local.toLocaleString()} ${inv.currency_local || ""}`
                        : `$${inv.amount_usd.toFixed(2)}`}
                    </td>
                    <td className="py-2 text-right">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        inv.status === "paid" ? "bg-emerald-500/20 text-emerald-400" :
                        inv.status === "pending" ? "bg-yellow-500/20 text-yellow-400" :
                        "bg-red-500/20 text-red-400"
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
