// AgentLink API Client

import type {
  AgentState,
  Stats,
  Analytics,
  ActiveAgentsResponse,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://192.168.178.102:8000';

class APIError extends Error {
  status: number;
  response?: unknown;

  constructor(
    message: string,
    status: number,
    response?: unknown
  ) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.response = response;
  }
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    // Try to parse JSON error, fallback to text
    let errorData: unknown = {};
    try {
      errorData = await response.json();
    } catch {
      // If JSON parsing fails, get text content
      const text = await response.text().catch(() => '');
      if (text) {
        errorData = { message: text };
      }
    }
    
    throw new APIError(
      `API Error: ${response.statusText}`,
      response.status,
      errorData
    );
  }

  return response.json();
}

export const api = {
  // States
  async getStates(params?: {
    agent_id?: string;
    status?: string;
    limit?: number;
  }): Promise<AgentState[]> {
    const query = new URLSearchParams();
    if (params?.agent_id) query.set('agent_id', params.agent_id);
    if (params?.status) query.set('status', params.status);
    if (params?.limit) query.set('limit', params.limit.toString());

    const url = `${API_BASE}/states${query.toString() ? '?' + query : ''}`;
    return fetchJSON<AgentState[]>(url);
  },

  async getState(stateId: string): Promise<AgentState> {
    return fetchJSON<AgentState>(`${API_BASE}/states/${stateId}`);
  },

  async createState(state: AgentState): Promise<AgentState> {
    return fetchJSON<AgentState>(`${API_BASE}/states`, {
      method: 'POST',
      body: JSON.stringify(state),
    });
  },

  async deleteState(stateId: string): Promise<{ deleted: string }> {
    return fetchJSON<{ deleted: string }>(`${API_BASE}/states/${stateId}`, {
      method: 'DELETE',
    });
  },

  // Analytics & Stats
  async getStats(): Promise<Stats> {
    return fetchJSON<Stats>(`${API_BASE}/api/stats`);
  },

  async getAnalytics(hours = 24): Promise<Analytics> {
    return fetchJSON<Analytics>(`${API_BASE}/api/analytics?hours=${hours}`);
  },

  async getActiveAgents(): Promise<ActiveAgentsResponse> {
    return fetchJSON<ActiveAgentsResponse>(`${API_BASE}/api/agents/active`);
  },
};

export { APIError };
