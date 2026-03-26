import { useEffect, useRef } from "react";
import { api, setStoredToken } from "../api";

interface Props {
  onLogin: () => void;
}

export default function Login({ onLogin }: Props) {
  const widgetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!widgetRef.current) return;

    window.TelegramLoginWidget = {
      dataOnauth: async (user: TelegramUser) => {
        try {
          const res = await api.telegramLogin(user as unknown as Record<string, unknown>);
          setStoredToken(res.access_token);
          onLogin();
        } catch (e) {
          alert("Login xatosi: " + (e as Error).message);
        }
      },
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", "devOpsmkbot");
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-onauth", "TelegramLoginWidget.dataOnauth(user)");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    widgetRef.current.appendChild(script);

    return () => {
      if (widgetRef.current) widgetRef.current.innerHTML = "";
    };
  }, [onLogin]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <div className="w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <div className="mb-3 text-4xl">🤖</div>
          <h1 className="text-2xl font-bold text-white">DevOps AI Agent</h1>
          <p className="mt-2 text-sm text-slate-400">
            Serverlarni sun'iy intellekt orqali boshqaring
          </p>
        </div>

        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-800/50 p-4 text-center text-sm text-slate-300">
          Tizimga kirish uchun Telegram akkauntingizdan foydalaning
        </div>

        <div className="flex justify-center" ref={widgetRef} />

        <p className="mt-6 text-center text-xs text-slate-500">
          Telegram orqali xavfsiz autentifikatsiya
        </p>
      </div>
    </div>
  );
}
