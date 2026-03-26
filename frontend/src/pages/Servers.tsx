import { useEffect, useState } from "react";
import { api, type Server } from "../api";
import ServerCard from "../components/ServerCard";

type FormData = Omit<Server, "id" | "created_at"> & { ssh_password: string };

const empty: FormData = {
  name: "",
  host: "",
  port: 22,
  user: "root",
  auth_type: "password",
  key_path: "",
  ssh_password: "",
};

const AUTH_TYPES = [
  { value: "password", label: "Parol", desc: "IP, port, login va parol" },
  { value: "ssh_key", label: "SSH Kalit fayl", desc: "Konteynerda fayl yo'li" },
  { value: "key_b64", label: "SSH Kalit (env)", desc: "SSH_PRIVATE_KEY_B64 muhit o'zgaruvchisi" },
];

type MetricsSnap = { cpu: number | null; ram: number | null; disk: number | null };

function Field({
  label, required, children,
}: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1">
        {label}{required && <span className="text-rose-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function inp(extra?: string) {
  return `w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none ${extra || ""}`;
}

function ServerForm({
  value,
  onChange,
  onSubmit,
  submitLabel,
  onCancel,
}: {
  value: FormData;
  onChange: (v: FormData) => void;
  onSubmit: (e: React.FormEvent) => void;
  submitLabel: string;
  onCancel?: () => void;
}) {
  const set = (patch: Partial<FormData>) => onChange({ ...value, ...patch });

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {/* Auth type tabs */}
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2">Ulanish usuli</label>
        <div className="flex rounded-lg overflow-hidden border border-slate-700">
          {AUTH_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => set({ auth_type: t.value, key_path: "", ssh_password: "" })}
              className={`flex-1 py-2 px-3 text-xs font-medium transition text-center ${
                value.auth_type === t.value
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-1">
          {AUTH_TYPES.find((t) => t.value === value.auth_type)?.desc}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Server nomi (alias)" required>
          <input
            required
            className={inp()}
            placeholder="masalan: main-server"
            value={value.name}
            onChange={(e) => set({ name: e.target.value })}
          />
        </Field>
        <Field label="IP manzil yoki DNS" required>
          <input
            required
            className={inp()}
            placeholder="192.168.1.100 yoki example.com"
            value={value.host}
            onChange={(e) => set({ host: e.target.value })}
          />
        </Field>
        <Field label="SSH port">
          <input
            type="number"
            className={inp()}
            placeholder="22"
            min={1}
            max={65535}
            value={value.port}
            onChange={(e) => set({ port: Number(e.target.value) || 22 })}
          />
        </Field>
        <Field label="SSH foydalanuvchi">
          <input
            className={inp()}
            placeholder="root"
            value={value.user}
            onChange={(e) => set({ user: e.target.value })}
          />
        </Field>
      </div>

      {/* Auth-specific fields */}
      {value.auth_type === "password" && (
        <Field label="SSH parol" required>
          <input
            type="password"
            className={inp()}
            placeholder="••••••••"
            value={value.ssh_password}
            onChange={(e) => set({ ssh_password: e.target.value })}
          />
        </Field>
      )}
      {value.auth_type === "ssh_key" && (
        <Field label="SSH kalit fayl yo'li (konteyner ichida)">
          <input
            className={inp("font-mono text-xs")}
            placeholder="/ssh-keys/id_rsa"
            value={value.key_path || ""}
            onChange={(e) => set({ key_path: e.target.value || null })}
          />
          <p className="text-xs text-slate-500 mt-1">
            Kalit docker-compose volumes orqali mount qilinishi kerak
          </p>
        </Field>
      )}
      {value.auth_type === "key_b64" && (
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
          <strong className="text-slate-300">SSH_PRIVATE_KEY_B64</strong> muhit o'zgaruvchisini{" "}
          <code className="text-emerald-400">.env</code> fayliga qo'shing:
          <pre className="mt-1 text-slate-500 font-mono">
            SSH_PRIVATE_KEY_B64=$(cat ~/.ssh/id_rsa | base64 -w0)
          </pre>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          className="flex-1 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 transition"
        >
          {submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white text-sm transition"
          >
            Bekor
          </button>
        )}
      </div>
    </form>
  );
}

export default function Servers() {
  const [list, setList] = useState<Server[]>([]);
  const [metricsMap, setMetricsMap] = useState<Record<number, MetricsSnap | null>>({});
  const [form, setForm] = useState<FormData>(empty);
  const [editing, setEditing] = useState<(Server & { ssh_password: string }) | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = () =>
    api
      .listServers()
      .then(async (servers) => {
        setList(servers);
        const next: Record<number, MetricsSnap | null> = {};
        await Promise.all(
          servers.map(async (s) => {
            try {
              const r = await api.serverMetricsRecent(s.id, 48);
              const p = r.points.at(-1);
              next[s.id] = p ? { cpu: p.cpu ?? null, ram: p.ram ?? null, disk: p.disk ?? null } : null;
            } catch {
              next[s.id] = null;
            }
          })
        );
        setMetricsMap(next);
      })
      .catch((e: Error) => setErr(e.message));

  useEffect(() => { load(); }, []);

  const saveNew = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErr(null);
    try {
      await api.createServer(form);
      setForm(empty);
      load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setSaving(true);
    setErr(null);
    try {
      await api.updateServer(editing.id, {
        name: editing.name,
        host: editing.host,
        port: editing.port,
        user: editing.user,
        auth_type: editing.auth_type,
        key_path: editing.key_path,
        ssh_password: editing.ssh_password || undefined,
      });
      setEditing(null);
      load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("O'chirishni tasdiqlaysizmi?")) return;
    try {
      await api.deleteServer(id);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const authBadge = (t: string) => {
    const map: Record<string, string> = {
      password: "bg-blue-500/20 text-blue-300",
      ssh_key: "bg-purple-500/20 text-purple-300",
      key_b64: "bg-orange-500/20 text-orange-300",
    };
    return map[t] || "bg-slate-700 text-slate-300";
  };

  const authLabel = (t: string) => {
    const map: Record<string, string> = { password: "Parol", ssh_key: "SSH Kalit", key_b64: "Key (env)" };
    return map[t] || t;
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Serverlar</h1>
        <p className="mt-1 text-slate-400">
          Server alias nomlarini buyruqlarda ishlatish mumkin: <span className="text-emerald-400">"main-server da nginx qayta ishga tushuр"</span>
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-rose-900/50 bg-rose-950/40 p-3 text-sm text-rose-300">
          {err}
          <button className="ml-2 underline" onClick={() => setErr(null)}>yopish</button>
        </div>
      )}

      {list.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((s) => (
            <ServerCard key={s.id} server={s} metrics={metricsMap[s.id] ?? null} />
          ))}
        </div>
      )}

      {/* Add server form */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
        <h2 className="text-lg font-medium text-white mb-4">Yangi server qo'shish</h2>
        <ServerForm
          value={form}
          onChange={setForm}
          onSubmit={saving ? (e) => e.preventDefault() : saveNew}
          submitLabel={saving ? "Saqlanmoqda…" : "Qo'shish"}
        />
      </div>

      {/* Servers table */}
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Nom</th>
              <th className="px-4 py-3 font-medium">Host : Port</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Auth</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-950/50">
            {list.map((s) => (
              <tr key={s.id} className="text-slate-200">
                <td className="px-4 py-3 font-medium">{s.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-400">
                  {s.host}:{s.port || 22}
                </td>
                <td className="px-4 py-3">{s.user}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${authBadge(s.auth_type)}`}>
                    {authLabel(s.auth_type)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    className="mr-3 text-emerald-400 hover:underline text-sm"
                    onClick={() => setEditing({ ...s, ssh_password: "" })}
                  >
                    Tahrirlash
                  </button>
                  <button
                    type="button"
                    className="text-rose-400 hover:underline text-sm"
                    onClick={() => remove(s.id)}
                  >
                    O'chirish
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {list.length === 0 && (
          <p className="p-8 text-center text-slate-500">
            Hali server qo'shilmagan. Yuqoridagi forma orqali qo'shing.
          </p>
        )}
      </div>

      {/* Edit modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-lg font-medium text-white mb-4">
              Serverni tahrirlash — <span className="text-emerald-400">{editing.name}</span>
            </h3>
            <ServerForm
              value={editing}
              onChange={(v) => setEditing({ ...editing, ...v })}
              onSubmit={saving ? (e) => e.preventDefault() : saveEdit}
              submitLabel={saving ? "Saqlanmoqda…" : "Saqlash"}
              onCancel={() => setEditing(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
