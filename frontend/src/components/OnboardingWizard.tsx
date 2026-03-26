import { useEffect, useState } from "react";
import { api } from "../api";

const STEPS = [
  {
    title: "Xush kelibsiz!",
    desc: "DevOps AI Agent — serverlaringizni tabiiy til orqali boshqarish platformasi.",
    action: null,
  },
  {
    title: "Server qo'shing",
    desc: "Birinchi serveringizni qo'shing. SSH kirimlari xavfsiz saqlanadi.",
    action: { label: "Serverlar sahifasiga o'ting", href: "/servers" },
  },
  {
    title: "AI token sozlang",
    desc: "OpenAI yoki Anthropic API kalitini qo'shing yoki tizim kreditidan foydalaning.",
    action: { label: "AI tokenlar", href: "/credentials/tokens" },
  },
  {
    title: "Birinchi vazifani yuboring",
    desc: "Dashboard'ga o'ting va \"nginx qayta ishga tushur\" kabi buyruq yuboring.",
    action: { label: "Dashboard", href: "/" },
  },
  {
    title: "Tayor!",
    desc: "Siz DevOps AI Agent'dan foydalanishga tayyorsiz. Savollar uchun Telegram: @devOpsmkbot",
    action: null,
  },
];

export default function OnboardingWizard({ onComplete }: { onComplete?: () => void }) {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [show, setShow] = useState(false);

  useEffect(() => {
    api.getOnboarding()
      .then((ob: { step: number; completed_at: string | null }) => {
        if (!ob.completed_at) {
          setStep(ob.step);
          setShow(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function advance() {
    const next = step + 1;
    setSaving(true);
    try {
      await api.updateOnboarding(next);
      if (next >= STEPS.length) {
        setShow(false);
        onComplete?.();
      } else {
        setStep(next);
      }
    } catch (_) {
      setStep(next);
    } finally {
      setSaving(false);
    }
  }

  async function skip() {
    setSaving(true);
    try {
      await api.updateOnboarding(STEPS.length);
    } catch (_) {}
    setShow(false);
    onComplete?.();
    setSaving(false);
  }

  if (loading || !show) return null;

  const current = STEPS[step] || STEPS[STEPS.length - 1];
  const isLast = step >= STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">
        {/* Progress dots */}
        <div className="flex gap-1.5 mb-6">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-emerald-500" : "bg-slate-700"
              }`}
            />
          ))}
        </div>

        <div className="text-xs text-slate-500 mb-1">
          {step + 1} / {STEPS.length} qadam
        </div>
        <h2 className="text-xl font-bold text-white mb-3">{current.title}</h2>
        <p className="text-slate-400 text-sm mb-6">{current.desc}</p>

        {current.action && (
          <a
            href={current.action.href}
            className="block mb-4 text-center py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 text-sm font-medium transition"
          >
            {current.action.label} →
          </a>
        )}

        <div className="flex gap-3">
          <button
            onClick={advance}
            disabled={saving}
            className="flex-1 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold transition disabled:opacity-50"
          >
            {isLast ? "Boshlash!" : "Keyingisi"}
          </button>
          {!isLast && (
            <button
              onClick={skip}
              disabled={saving}
              className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 text-sm transition disabled:opacity-50"
            >
              O'tkazib yuborish
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
