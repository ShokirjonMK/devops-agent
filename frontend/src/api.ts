const base = "";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Server = {
  id: number;
  name: string;
  host: string;
  user: string;
  auth_type: string;
  key_path: string | null;
  created_at: string;
};

export type TaskStep = {
  id: number;
  task_id: number;
  step_order: number;
  command: string | null;
  output: string | null;
  status: string;
  explanation: string | null;
  phase: string | null;
  created_at: string;
};

export type AuditLog = {
  id: number;
  task_id: number;
  message: string;
  level: string;
  timestamp: string;
};

export type Task = {
  id: number;
  user_id: string | null;
  server_id: number | null;
  command_text: string;
  status: string;
  source: string;
  summary: string | null;
  created_at: string;
};

export type TaskDetail = Task & {
  steps: TaskStep[];
  logs: AuditLog[];
};

export const api = {
  listServers: () => http<Server[]>("/api/servers"),
  createServer: (body: Omit<Server, "id" | "created_at">) =>
    http<Server>("/api/servers", { method: "POST", body: JSON.stringify(body) }),
  updateServer: (id: number, body: Partial<Omit<Server, "id" | "created_at">>) =>
    http<Server>(`/api/servers/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteServer: (id: number) => http<void>(`/api/servers/${id}`, { method: "DELETE" }),

  listTasks: () => http<Task[]>("/api/tasks?limit=100"),
  getTask: (id: number) => http<TaskDetail>(`/api/tasks/${id}`),
  createTask: (command_text: string, server_id?: number | null) =>
    http<Task>("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ command_text, server_id: server_id ?? null }),
    }),
};
