import type { 
  AskRequest, AskResponse, DashboardResponse, SchemaResponse, HistoryItem,
  User, Client, Dataset, Report, AdminDashboardResponse, ClientProfileResponse,
  LibraryDataset
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getHeaders(contentType: string | null = 'application/json'): Record<string, string> {
  const headers: Record<string, string> = {};
  if (contentType) {
    headers['Content-Type'] = contentType;
  }
  const token = localStorage.getItem('token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorText = '';
    try {
      const errorJson = await response.json();
      errorText = errorJson.detail || errorJson.message;
    } catch {
      errorText = await response.text();
    }
    throw new Error(errorText || `API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  // --- AUTHENTICATION ---
  async login(email: string, password: string): Promise<{ access_token: string; role: string; name: string }> {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await handleResponse<{ access_token: string; token_type: string; role: string; name: string }>(res);
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('role', data.role);
    localStorage.setItem('userName', data.name);
    return { access_token: data.access_token, role: data.role, name: data.name };
  },

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('userName');
  },

  async getCurrentUser(): Promise<User> {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: getHeaders()
    });
    return handleResponse<User>(res);
  },

  // --- HEALTH CHECK ---
  async getHealth(): Promise<{ status: string; timestamp: string }> {
    const res = await fetch(`${API_URL}/api/health`);
    return handleResponse(res);
  },

  // --- DYNAMIC DATA EXPLORER & ASK INSIGHTS ---
  async getDashboard(datasetId?: number): Promise<DashboardResponse> {
    const url = datasetId ? `${API_URL}/api/dashboard?dataset_id=${datasetId}` : `${API_URL}/api/dashboard`;
    const res = await fetch(url, { headers: getHeaders() });
    return handleResponse(res);
  },

  async getSchema(datasetId?: number): Promise<SchemaResponse> {
    const url = datasetId ? `${API_URL}/api/schema?dataset_id=${datasetId}` : `${API_URL}/api/schema`;
    const res = await fetch(url, { headers: getHeaders() });
    return handleResponse(res);
  },

  async getHistory(): Promise<HistoryItem[]> {
    const res = await fetch(`${API_URL}/api/history`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async askQuestion(req: AskRequest, datasetId?: number): Promise<AskResponse> {
    const url = datasetId ? `${API_URL}/api/ask?dataset_id=${datasetId}` : `${API_URL}/api/ask`;
    const res = await fetch(url, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  // --- ADMIN PORTAL SERVICES ---
  async getAdminDashboard(): Promise<AdminDashboardResponse> {
    const res = await fetch(`${API_URL}/admin/dashboard`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async getClients(): Promise<Client[]> {
    const res = await fetch(`${API_URL}/admin/clients`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async createClient(clientData: any): Promise<Client> {
    const res = await fetch(`${API_URL}/admin/clients`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(clientData)
    });
    return handleResponse(res);
  },

  async getClientDetails(id: number): Promise<{ client: Client; stats: any; datasets: Dataset[]; reports: Report[] }> {
    const res = await fetch(`${API_URL}/admin/clients/${id}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async updateClient(id: number, clientData: any): Promise<Client> {
    const res = await fetch(`${API_URL}/admin/clients/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(clientData)
    });
    return handleResponse(res);
  },

  async deleteClient(id: number): Promise<any> {
    const res = await fetch(`${API_URL}/admin/clients/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    return handleResponse(res);
  },

  // --- CLIENT PORTAL SERVICES ---
  async getClientProfile(): Promise<ClientProfileResponse> {
    const res = await fetch(`${API_URL}/client/profile`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async updateClientProfile(profileData: any): Promise<ClientProfileResponse> {
    const res = await fetch(`${API_URL}/client/profile`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(profileData)
    });
    return handleResponse(res);
  },

  async getClientDatasets(): Promise<Dataset[]> {
    const res = await fetch(`${API_URL}/client/datasets?_t=${Date.now()}`, { 
      headers: {
        ...getHeaders(),
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      }
    });
    return handleResponse(res);
  },

  async getLibraryDatasets(): Promise<LibraryDataset[]> {
    const res = await fetch(`${API_URL}/client/datasets/library`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async importLibraryDataset(libraryId: string, customName?: string): Promise<Dataset> {
    const res = await fetch(`${API_URL}/client/datasets/library`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ library_id: libraryId, custom_name: customName })
    });
    return handleResponse(res);
  },

  async uploadDataset(name: string, file: File): Promise<Dataset> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    const res = await fetch(`${API_URL}/client/datasets`, {
      method: 'POST',
      headers: getHeaders(null), // multipart boundary will be auto-set by the browser
      body: formData
    });
    return handleResponse(res);
  },

  async deleteDataset(id: number): Promise<any> {
    const res = await fetch(`${API_URL}/client/datasets/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    return handleResponse(res);
  },

  async getClientReports(): Promise<Report[]> {
    const res = await fetch(`${API_URL}/client/reports`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async createReport(reportData: { name: string; report_type: string; dataset_id: number; content: string }): Promise<Report> {
    const res = await fetch(`${API_URL}/client/reports`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(reportData)
    });
    return handleResponse(res);
  },

  async deleteReport(id: number): Promise<any> {
    const res = await fetch(`${API_URL}/client/reports/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    return handleResponse(res);
  }
};
