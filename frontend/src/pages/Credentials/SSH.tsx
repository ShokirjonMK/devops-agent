import ReactMarkdown from "react-markdown";
import sshSetup from "@docs/SSH-SETUP.md?raw";

export default function SSHCredentialsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">SSH ulanish</h1>
        <p className="mt-1 text-slate-400">
          Kalit va parolni Web UI orqali `credential_vault` ga shifrlangan holda saqlang. Quyida to‘liq yo‘riqnoma.
        </p>
      </div>
      <article className="prose prose-invert prose-sm max-w-none rounded-xl border border-slate-800 bg-slate-900/40 p-6 prose-headings:text-slate-100 prose-pre:bg-black/50 prose-code:text-emerald-300">
        <ReactMarkdown>{sshSetup}</ReactMarkdown>
      </article>
    </div>
  );
}
