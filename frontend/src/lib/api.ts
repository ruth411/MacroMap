const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

interface ApiError {
  detail: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: "An unknown error occurred",
    }));
    throw new Error(error.detail);
  }
  return response.json();
}

export const api = {
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      credentials: "include",  // Send httpOnly cookies automatically
    });
    return handleResponse<T>(response);
  },

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",  // Send httpOnly cookies automatically
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  },

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      credentials: "include",  // Send httpOnly cookies automatically
    });
    return handleResponse<T>(response);
  },
};

// Health check
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  llm_provider?: string;
}

export async function checkHealth(): Promise<HealthResponse> {
  return api.get<HealthResponse>("/health");
}

// Chat API
export interface ChatRequest {
  message: string;
  session_id?: string;
  use_templates?: boolean;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  question_type: string | null;
  timestamp: string;
}

export interface ChatHealthResponse {
  service: string;
  provider: string;
  model: string;
  healthy: boolean;
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return api.post<ChatResponse>(`${API_PREFIX}/chat/`, request);
}

export async function clearConversation(sessionId: string = "default"): Promise<{ status: string; message: string }> {
  return api.post<{ status: string; message: string }>(`${API_PREFIX}/chat/clear`, { session_id: sessionId });
}

export async function deleteConversation(sessionId: string): Promise<{ status: string; message: string }> {
  return api.delete<{ status: string; message: string }>(`${API_PREFIX}/chat/${sessionId}`);
}

export async function checkChatHealth(): Promise<ChatHealthResponse> {
  return api.get<ChatHealthResponse>(`${API_PREFIX}/chat/health`);
}

// Session API
export interface SessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
}

export interface SessionMessage {
  role: "user" | "assistant";
  content: string;
  question_type?: string | null;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  title: string;
  created_at: string;
  messages: SessionMessage[];
}

export interface CreateSessionResponse {
  id: string;
  title: string;
  created_at: string;
}

export async function listSessions(limit: number = 50, offset: number = 0): Promise<SessionListResponse> {
  return api.get<SessionListResponse>(`${API_PREFIX}/chat/sessions?limit=${limit}&offset=${offset}`);
}

export async function createSession(title?: string): Promise<CreateSessionResponse> {
  return api.post<CreateSessionResponse>(`${API_PREFIX}/chat/sessions`, title ? { title } : {});
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return api.get<SessionDetail>(`${API_PREFIX}/chat/sessions/${sessionId}`);
}

export async function deleteSession(sessionId: string): Promise<{ status: string; message: string }> {
  return api.delete<{ status: string; message: string }>(`${API_PREFIX}/chat/sessions/${sessionId}`);
}
