import { useEffect, useState } from "react";
import { api, type Server } from "../api";

const empty: Omit<Server, "id" | "created_at"> = {
  name: "",
  host: "",
  user: "root",
  auth_type: "ssh_key",
  key_path: "/ssh-keys/id_rsa",
};

export default function Servers() {
  const [list, setList] = useState<Server[]>([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<Server | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = () =>
    api
      .listServers()
      .then(setList)
      .catch((e: Error) => setErr(e.message));

  useEffect(() => {
    load();
  }, []);

  const saveNew = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api.createServer(form);
      setForm(empty);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setErr(null);
    try {
      await api.updateServer(editing.id, {
        name: editing.name,
        host: editing.host,
        user: editing.user,
        auth_type: editing.auth_type,
        key_path: editing.key_path,
      });
      setEditing(null);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("O‘chirishni tasdiqlaysizmi?")) return;
    setErr(null);
    try {
      await api.deleteServer(id);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Serverlar</h1>
        <p className="mt-1 text-slate-400">
          Alias nomlari buyruqda ishlatiladi (masalan: &quot;sarbon serverida …&quot;). SSH kalit konteynerda
          mount yoki SSH_PRIVATE_KEY_B64 orqali beriladi.
        </p>
      </div>

      {err && <p className="rounded-lg border border-rose-900/50 bg-rose-950/40 p-3 text-sm text-rose-300">{err}</p>}

      <form
        onSubmit={saveNew}
        className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-5 sm:grid-cols-2"
      >
        <h2 className="sm:col-span-2 text-lg font-medium text-white">Yangi server</h2>
        <input
          required
          placeholder="name (alias)"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          required
          placeholder="host (IP yoki DNS)"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          value={form.host}
          onChange={(e) => setForm({ ...form, host: e.target.value })}
        />
        <input
          placeholder="SSH user"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          value={form.user}
          onChange={(e) => setForm({ ...form, user: e.target.value })}
        />
        <input
          placeholder="key_path (konteyner ichida)"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono text-xs"
          value={form.key_path || ""}
          onChange={(e) => setForm({ ...form, key_path: e.target.value || null })}
        />
        <button
          type="submit"
          className="sm:col-span-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        >
          Qo‘shish
        </button>
      </form>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Nom</th>
              <th className="px-4 py-3 font-medium">Host</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Kalit</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-950/50">
            {list.map((s) => (
              <tr key={s.id} className="text-slate-200">
                <td className="px-4 py-3 font-medium">{s.name}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.host}</td>
                <td className="px-4 py-3">{s.user}</td>
                <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-slate-500">{s.key_path}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    className="mr-2 text-emerald-400 hover:underline"
                    onClick={() => setEditing(s)}
                  >
                    Tahrirlash
                  </button>
                  <button type="button" className="text-rose-400 hover:underline" onClick={() => remove(s.id)}>
                    O‘chirish
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {list.length === 0 && <p className="p-6 text-center text-slate-500">Serverlar yo‘q.</p>}
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <form
            onSubmit={saveEdit}
            className="w-full max-w-lg space-y-3 rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl"
          >
            <h3 className="text-lg font-medium text-white">Serverni tahrirlash</h3>
            <input
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={editing.name}
              onChange={(e) => setEditing({ ...editing, name: e.target.value })}
            />
            <input
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={editing.host}
              onChange={(e) => setEditing({ ...editing, host: e.target.value })}
            />
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={editing.user}
              onChange={(e) => setEditing({ ...editing, user: e.target.value })}
            />
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono text-xs"
              value={editing.key_path || ""}
              onChange={(e) => setEditing({ ...editing, key_path: e.target.value || null })}
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                className="rounded-lg px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
                onClick={() => setEditing(null)}
              >
                Bekor
              </button>
              <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white">
                Saqlash
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
