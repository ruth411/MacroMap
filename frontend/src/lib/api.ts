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
      headers: {
        "Content-Type": "application/json",
      },
    });
    return handleResponse<T>(response);
  },

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  },

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
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
