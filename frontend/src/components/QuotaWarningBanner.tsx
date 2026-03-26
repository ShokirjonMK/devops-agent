import { useEffect, useState } from "react";
import { api } from "../api";

type Sub = {
  tasks_used_month: number;
  tasks_limit: number;
  servers_used: number;
  servers_limit: number;
  ai_credit_balance_usd: number;
};

export default function QuotaWarningBanner() {
  const [warnings, setWarnings] = useState<string[]>([]);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    api.getSubscription()
      .then((sub: Sub) => {
        const msgs: string[] = [];
        const taskPct = sub.tasks_limit > 0 ? (sub.tasks_used_month / sub.tasks_limit) * 100 : 0;
        if (taskPct >= 100) msgs.push("Vazifa limiti to'liq ishlatildi");
        else if (taskPct >= 80) msgs.push(`Vazifa limitining ${Math.round(taskPct)}% ishlatildi`);

        const srvPct = sub.servers_limit > 0 ? (sub.servers_used / sub.servers_limit) * 100 : 0;
        if (srvPct >= 100) msgs.push("Server limiti to'liq ishlatildi");
        else if (srvPct >= 80) msgs.push(`Server limitining ${Math.round(srvPct)}% ishlatildi`);

        if (sub.ai_credit_balance_usd > 0 && sub.ai_credit_balance_usd < 2) {
          msgs.push(`AI kredit balansi past: $${sub.ai_credit_balance_usd.toFixed(2)}`);
        }
        setWarnings(msgs);
      })
      .catch(() => {});
  }, []);

  if (dismissed || warnings.length === 0) return null;

  return (
    <div className="mb-4 rounded-lg border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 flex items-start justify-between gap-4">
      <div className="flex-1">
        {warnings.map((w, i) => (
          <div key={i} className="flex items-center gap-2 text-sm text-yellow-300">
            <span>⚠️</span>
            <span>{w}</span>
            {i === 0 && (
              <a href="/upgrade" className="ml-1 underline hover:text-yellow-200">
                Yangilash
              </a>
            )}
          </div>
        ))}
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-yellow-500 hover:text-yellow-300 text-lg leading-none"
      >
        ×
      </button>
    </div>
  );
}
