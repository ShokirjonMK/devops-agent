import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type TaskDetail as TD } from "../api";
import { useTaskStream } from "../hooks/useTaskStream";

function phaseIcon(phase: string | null | undefined) {
  const p = (phase || "").toLowerCase();
  if (p === "diagnose") return "🔍";
  if (p === "verify") return "✅";
  if (p === "execute") return "⚙️";
  return "•";
}

export default function TaskDetail() {
  const { id } = useParams();
  const [task, setTask] = useState<TD | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const numericId = id ? Number(id) : null;
  const { events, lines: streamLines, state: wsState } = useTaskStream(Number.isFinite(numericId) ? numericId : null);

  const load = () => {
    if (!id) return;
    api
      .getTask(Number(id))
      .then(setTask)
      .catch((e: Error) => setErr(e.message));
  };

  useEffect(() => {
    load();
    if (wsState === "connected") return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [id, wsState]);

  const thinking = events.filter((e) => e.type === "agent_thinking").length > 0 && task?.status === "running";

  if (err) {
    return (
      <div className="space-y-4">
        <Link to="/" className="text-sm text-emerald-400 hover:underline">
          ← Dashboard
        </Link>
        <p className="text-rose-400">{err}</p>
      </div>
    );
  }

  if (!task) {
    return <p className="text-slate-500">Yuklanmoqda…</p>;
  }

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-emerald-400 hover:underline">
        ← Dashboard
      </Link>
      <div>
        <h1 className="text-2xl font-semibold text-white">Vazifa #{task.id}</h1>
        <p className="mt-2 font-mono text-sm text-slate-300">{task.command_text}</p>
        <p className="mt-2 text-sm text-slate-500">
          {task.status} · {task.source}
          {task.user_id && ` · user: ${task.user_id}`}
        </p>
        {thinking && (
          <p className="mt-2 animate-pulse text-sm text-sky-300">
            Agent fikrlayapti
            <span className="inline-block w-6 text-left">…</span>
          </p>
        )}
        {task.summary && (
          <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Xulosa</p>
            <p className="mt-1 text-slate-200">{task.summary}</p>
          </div>
        )}
      </div>

      {(streamLines.length > 0 || wsState !== "closed") && (
        <section>
          <h2 className="mb-3 text-lg font-medium text-white">
            Real-time <span className="text-slate-500">· {wsState}</span>
          </h2>
          <pre className="max-h-56 overflow-auto rounded-lg border border-slate-800 bg-[#0d1117] p-3 font-mono text-xs leading-relaxed text-green-100/90">
            {streamLines.slice(-40).join("\n")}
          </pre>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-medium text-white">Timeline</h2>
        <ol className="space-y-3 border-l border-slate-800 pl-4">
          {task.steps.map((s) => (
            <li key={s.id} className="relative">
              <span className="absolute -left-[21px] top-1.5 text-sm" aria-hidden>
                {phaseIcon(s.phase)}
              </span>
              <p className="text-xs text-slate-500">{new Date(s.created_at).toLocaleString()}</p>
              {s.command && (
                <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-950 p-2 font-mono text-xs text-emerald-300">
                  {s.command}
                </pre>
              )}
              {s.phase && (
                <p className="mt-1 text-xs font-medium uppercase tracking-wide text-sky-400/90">bosqich: {s.phase}</p>
              )}
              {s.explanation && (
                <p className="mt-1 rounded-md border border-slate-700/80 bg-slate-900/80 px-2 py-1.5 text-xs text-slate-300">
                  <span className="text-slate-500">Nima uchun: </span>
                  {s.explanation}
                </p>
              )}
              <p className="mt-1 text-xs text-slate-400">status: {s.status}</p>
              {s.output && (
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-slate-800 bg-black/40 p-3 font-mono text-xs text-slate-300">
                  {s.output}
                </pre>
              )}
            </li>
          ))}
        </ol>
        {task.steps.length === 0 && <p className="text-slate-500">Hali qadamlar yo‘q.</p>}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium text-white">Audit jurnali</h2>
        <ul className="space-y-2">
          {task.logs.map((l) => (
            <li key={l.id} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm">
              <span className="text-xs text-slate-500">{new Date(l.timestamp).toLocaleString()}</span>
              <span className="ml-2 text-xs text-slate-600">[{l.level}]</span>
              <p className="text-slate-300">{l.message}</p>
            </li>
          ))}
        </ul>
        {task.logs.length === 0 && <p className="text-slate-500">Log yo‘q.</p>}
      </section>
    </div>
  );
}
