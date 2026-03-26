const base = "";

const TOKEN_KEY = "devops_agent_access_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const t = getStoredToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
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
  environment?: string;
  monitoring_enabled?: boolean;
  monitoring_interval_minutes?: number;
  last_check_status?: string;
  last_check_at?: string | null;
  server_metadata?: Record<string, unknown>;
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
  owner_user_id: string | null;
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

export type AiKeyMeta = {
  id: string;
  name: string;
  provider: "openai" | "anthropic";
  created_at: string | null;
};

export type AiKeyCreate = {
  name?: string;
  provider: "openai" | "anthropic";
  api_key: string;
  base_url?: string | null;
  model?: string | null;
};

export type AuthToken = {
  access_token: string;
  token_type: string;
};

export const api = {
  telegramLogin: (data: Record<string, unknown>) =>
    http<AuthToken>("/api/auth/telegram", {
      method: "POST",
      body: JSON.stringify(data),
    }),


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

  listAiKeys: () =>
    http<AiKeyMeta[]>("/api/ai-keys"),
  createAiKey: (body: AiKeyCreate) =>
    http<AiKeyMeta>("/api/ai-keys", { method: "POST", body: JSON.stringify(body) }),
  deleteAiKey: (id: string) => http<void>(`/api/ai-keys/${id}`, { method: "DELETE" }),

  listAiTokenProviders: () => http<Record<string, { base_url: string | null; models: string[] }>>(
    "/api/ai-tokens/providers"
  ),
  listAiTokens: () =>
    http<
      {
        id: string;
        provider: string;
        name: string;
        is_default: boolean;
        is_active: boolean;
        usage_this_month_usd: string;
        monthly_budget_usd: string | null;
      }[]
    >("/api/ai-tokens"),
  createAiToken: (body: {
    provider: string;
    name: string;
    token_value: string;
    base_url?: string | null;
    model_override?: string | null;
    monthly_budget_usd?: string | null;
    is_default?: boolean;
  }) => http<unknown>("/api/ai-tokens", { method: "POST", body: JSON.stringify(body) }),
  deleteAiToken: (id: string) => http<void>(`/api/ai-tokens/${id}`, { method: "DELETE" }),
  testAiToken: (id: string) =>
    http<{ success: boolean; latency_ms: number; model_used: string; detail: string | null }>(
      `/api/ai-tokens/${id}/test`,
      { method: "POST" }
    ),

  adminOverview: () =>
    http<{
      total_users: number;
      active_users_today: number;
      total_tasks_today: number;
      total_tasks_week: number;
      success_rate_percent: number;
      total_ai_cost_month_usd: number;
      total_servers: number;
      servers_online: number;
    }>("/api/admin/stats/overview"),
  adminUsers: () =>
    http<
      {
        id: string;
        telegram_id: number;
        username: string | null;
        role: string;
        is_active: boolean;
        tasks_count: number;
        servers_count?: number;
      }[]
    >("/api/admin/users"),
  adminSetUserRole: (userId: string, role: string) =>
    http<unknown>(`/api/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  adminSetUserActive: (userId: string, is_active: boolean) =>
    http<unknown>(`/api/admin/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active }),
    }),
  adminSettings: () =>
    http<{ key: string; value: unknown; description: string | null; updated_at: string | null }[]>(
      "/api/admin/settings"
    ),
  adminPatchSetting: (key: string, value: unknown) =>
    http<unknown>(`/api/admin/settings/${encodeURIComponent(key)}`, {
      method: "PATCH",
      body: JSON.stringify({ value }),
    }),
  adminSystemAi: () => http<{ provider: string; model: string; key_hint: string }[]>("/api/admin/system-ai"),
  adminUpsertSystemAi: (body: { provider: string; api_key: string; model: string }) =>
    http<unknown>("/api/admin/system-ai", { method: "POST", body: JSON.stringify(body) }),
  adminAuditLogs: (q?: string) => http<unknown[]>(`/api/admin/audit-logs${q ?? ""}`),
  adminAuditExportCsv: () =>
    fetch(`${base}/api/admin/audit-logs?export=csv`, { headers: authHeaders() }).then((r) => {
      if (!r.ok) throw new Error(r.statusText);
      return r.text();
    }),

  analyticsSummary: () =>
    http<{
      tasks_total_30d: number;
      success_rate_percent: number;
      uptime_percent: number;
      ai_cost_month_usd: number;
      series_tasks_by_day: { day: string; ok: number; bad: number }[];
      ai_cost_by_provider: { name: string; value: number }[];
      server_uptime_bars: { name: string; uptime_score: number }[];
      activity_heatmap: { day: string; count: number }[];
    }>("/api/analytics/summary"),

  analyticsServerMetrics: (serverId: number, hours = 168) =>
    http<{ points: { t: string | null; cpu: number | null; ram: number | null; disk: number | null }[] }>(
      `/api/analytics/servers/${serverId}/metrics?hours=${hours}`
    ),

  serverMetricsRecent: (serverId: number, hours = 24) =>
    http<{ points: { t: string | null; cpu: number | null; ram: number | null; disk: number | null }[] }>(
      `/api/servers/${serverId}/metrics/recent?hours=${hours}`
    ),

  patchAiToken: (
    id: string,
    body: Partial<{
      is_active: boolean;
      is_default: boolean;
      monthly_budget_usd: string | null;
      model_override: string | null;
      base_url: string | null;
    }>
  ) => http<unknown>(`/api/ai-tokens/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};
