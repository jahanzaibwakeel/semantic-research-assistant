export type DocumentItem = {
  id: string;
  project_id: string | null;
  filename: string;
  document_type: string;
  source_url: string | null;
  title: string | null;
  tags: string | null;
  status: string;
  page_count: number;
  chunk_count: number;
  summary: string | null;
  key_points: string | null;
  error_message: string | null;
  processed_at: string | null;
  indexed_at: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Project = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type Team = {
  id: string;
  name: string;
  description: string | null;
  allowed_api_scopes: string;
  api_key_daily_limit: number | null;
  created_at: string;
  updated_at: string;
};

export type TeamMember = {
  id: string;
  team_id: string;
  user_id: string;
  email: string;
  role: string;
  created_at: string;
};

export type SavedQuery = {
  id: string;
  title: string;
  query: string;
  mode: string;
  project_id: string | null;
  created_at: string;
};

export type ResearchNote = {
  id: string;
  title: string;
  body: string;
  project_id: string | null;
  document_id: string | null;
  pinned: boolean;
  created_at: string;
  updated_at: string;
};

export type UsageSummary = {
  operation: string;
  calls: number;
  estimated_tokens: number;
};

export type EvaluationRecord = {
  id: string;
  document_id: string | null;
  question: string;
  source_count: number;
  cited_source_count: number;
  unsupported_citation_count: number;
  groundedness_score: number;
  notes: string | null;
  created_at: string;
};

export type ApiKeyRecord = {
  id: string;
  team_id: string | null;
  name: string;
  key_prefix: string;
  scopes: string;
  daily_request_limit: number | null;
  requests_today: number;
  revoked: boolean;
  last_used_at: string | null;
  created_at: string;
};

export type ApiKeyCreated = ApiKeyRecord & {
  api_key: string;
};

export type OperationalStatus = {
  documents_by_status: Record<string, number>;
  documents_by_type: Record<string, number>;
  recent_failures: DocumentItem[];
};

export type AdminOverview = {
  users: {
    id: string;
    email: string;
    full_name: string | null;
    document_count: number;
    api_key_count: number;
    created_at: string;
  }[];
  failed_jobs: {
    document_id: string;
    owner_email: string;
    filename: string;
    status: string;
    error_message: string | null;
    updated_at: string;
  }[];
  storage: {
    backend: string;
    local_upload_bytes: number;
    local_upload_files: number;
  };
};

export type Citation = {
  document_id: string;
  filename: string;
  page: number | null;
  chunk_index: number | null;
  score: number | null;
  vector_score: number | null;
  keyword_score: number | null;
  retrieval_method: string;
  excerpt: string;
};

export type LiteratureMatrixRow = {
  document_id: string;
  filename: string;
  title: string | null;
  authors: string | null;
  year: string | null;
  methods: string | null;
  datasets: string | null;
  claims: string | null;
  findings: string | null;
  limitations: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function api<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  return request<T>(path, token, init, true);
}

async function request<T>(path: string, token: string | null, init: RequestInit = {}, allowRefresh: boolean): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (response.status === 401 && allowRefresh && typeof window !== "undefined") {
    const refreshToken = localStorage.getItem("research_refresh_token");
    if (refreshToken) {
      const refreshed = await request<{ access_token: string; refresh_token: string }>("/auth/refresh", null, {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken })
      }, false);
      localStorage.setItem("research_token", refreshed.access_token);
      localStorage.setItem("research_refresh_token", refreshed.refresh_token);
      return request<T>(path, refreshed.access_token, init, false);
    }
  }
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);
  return api<{ access_token: string; refresh_token: string; user: { email: string; full_name: string | null } }>("/auth/login", null, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });
}

export async function register(email: string, password: string, full_name?: string) {
  return api<{ access_token: string; refresh_token: string; user: { email: string; full_name: string | null } }>("/auth/register", null, {
    method: "POST",
    body: JSON.stringify({ email, password, full_name })
  });
}

export async function logout(token: string | null, refreshToken: string | null) {
  if (!token) return;
  await api<void>("/auth/logout", token, {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken })
  });
}

export async function changePassword(token: string, currentPassword: string, newPassword: string) {
  await api<void>("/auth/change-password", token, {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
  });
}

export async function createApiKey(token: string, name: string, scopes: string[] = ["*"], dailyRequestLimit: number | null = null, teamId: string | null = null) {
  return api<ApiKeyCreated>("/auth/api-keys", token, {
    method: "POST",
    body: JSON.stringify({ name, scopes, daily_request_limit: dailyRequestLimit, team_id: teamId })
  });
}

export async function revokeApiKey(token: string, apiKeyId: string) {
  await api<void>(`/auth/api-keys/${apiKeyId}`, token, { method: "DELETE" });
}

export async function downloadText(path: string, token: string | null): Promise<string> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { headers });
  if (!response.ok) throw new Error(await response.text());
  return response.text();
}

export async function downloadBlob(path: string, token: string | null): Promise<Blob> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { headers });
  if (!response.ok) throw new Error(await response.text());
  return response.blob();
}

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}
