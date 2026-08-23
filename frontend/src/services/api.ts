import type { AskRequest, AskResponse, DashboardResponse, SchemaResponse, HistoryItem } from '../types';

// Read API base URL from import.meta.env or default to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<{ status: string; timestamp: string }> {
    const res = await fetch(`${API_URL}/api/health`);
    return handleResponse(res);
  },

  async getDashboard(): Promise<DashboardResponse> {
    const res = await fetch(`${API_URL}/api/dashboard`);
    return handleResponse(res);
  },

  async getSchema(): Promise<SchemaResponse> {
    const res = await fetch(`${API_URL}/api/schema`);
    return handleResponse(res);
  },

  async getHistory(): Promise<HistoryItem[]> {
    const res = await fetch(`${API_URL}/api/history`);
    return handleResponse(res);
  },

  async askQuestion(req: AskRequest): Promise<AskResponse> {
    const res = await fetch(`${API_URL}/api/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },
};
