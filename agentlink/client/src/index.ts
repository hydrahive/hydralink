/**
 * AgentLink TypeScript Client
 * Client library for Agent-to-Agent State Protocol
 */

import { WebSocket } from 'ws';
import type {
  AgentState,
  StateFilter,
  HealthResponse
} from './types';

export * from './types';

export interface AgentLinkConfig {
  url: string;
  agentId: string;
  secret?: string;
  reconnect?: boolean;
  maxReconnectDelay?: number;
}

export class AgentLinkClient {
  private apiUrl: string;
  private agentId: string;
  private secret?: string;
  private ws?: WebSocket;
  private reconnectAttempts = 0;
  private maxReconnectDelay: number;
  private reconnectEnabled: boolean;
  private onStateUpdateCallback?: (state: AgentState) => void;

  constructor(config: AgentLinkConfig) {
    this.apiUrl = config.url.replace(/\/$/, ''); // Remove trailing slash
    this.agentId = config.agentId;
    this.secret = config.secret;
    this.reconnectEnabled = config.reconnect ?? true;
    this.maxReconnectDelay = config.maxReconnectDelay ?? 30000; // 30s default
  }

  // ============================================================================
  // REST API
  // ============================================================================

  /**
   * Create a new agent state
   */
  async createState(state: Partial<AgentState>): Promise<AgentState> {
    const fullState: AgentState = {
      agent_id: state.agent_id || this.agentId,
      task: state.task!,
      context: state.context || {},
      knowledge: state.knowledge || {},
      working_memory: state.working_memory || {},
      handoff: state.handoff || null,
      ...state
    } as AgentState;

    const response = await fetch(`${this.apiUrl}/states`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(fullState)
    });

    if (!response.ok) {
      throw new Error(`Failed to create state: ${response.statusText}`);
    }

    return await response.json() as AgentState;
  }

  /**
   * Get a state by ID
   */
  async getState(id: string): Promise<AgentState> {
    const response = await fetch(`${this.apiUrl}/states/${id}`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`State not found: ${id}`);
      }
      throw new Error(`Failed to get state: ${response.statusText}`);
    }

    return await response.json() as AgentState;
  }

  /**
   * List states with optional filters
   */
  async listStates(filter?: StateFilter): Promise<AgentState[]> {
    const params = new URLSearchParams();
    if (filter?.agent_id) params.append('agent_id', filter.agent_id);
    if (filter?.status) params.append('status', filter.status);
    if (filter?.limit) params.append('limit', filter.limit.toString());

    const url = `${this.apiUrl}/states` + (params.toString() ? `?${params}` : '');
    const response = await fetch(url, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`Failed to list states: ${response.statusText}`);
    }

    return await response.json() as AgentState[];
  }

  /**
   * Get health status
   */
  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.apiUrl}/health`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return await response.json() as HealthResponse;
  }

  // ============================================================================
  // WebSocket (Real-time updates)
  // ============================================================================

  /**
   * Connect to WebSocket for real-time state updates
   */
  connect(onStateUpdate: (state: AgentState) => void): void {
    this.onStateUpdateCallback = onStateUpdate;
    this.connectWebSocket();
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    this.reconnectEnabled = false;
    if (this.ws) {
      this.ws.close();
      this.ws = undefined;
    }
  }

  // ============================================================================
  // Private Methods
  // ============================================================================

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    if (this.secret) {
      headers['X-AgentLink-Secret'] = this.secret;
    }

    return headers;
  }

  private connectWebSocket(): void {
    const wsUrl = this.apiUrl.replace(/^http/, 'ws') + '/ws';

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.on('open', () => {
        console.log('[AgentLink] WebSocket connected');
        this.reconnectAttempts = 0;

        // Subscribe to this agent's states
        if (this.ws) {
          this.ws.send(JSON.stringify({
            action: 'subscribe',
            agent_id: this.agentId
          }));
        }
      });

      this.ws.on('message', (data: Buffer) => {
        try {
          const message = JSON.parse(data.toString());
          
          // Check if it's a state update
          if (message.id && message.agent_id && this.onStateUpdateCallback) {
            this.onStateUpdateCallback(message as AgentState);
          }
        } catch (error: unknown) {
          console.error('[AgentLink] Failed to parse WebSocket message:', error);
        }
      });

      this.ws.on('close', () => {
        console.log('[AgentLink] WebSocket disconnected');
        this.ws = undefined;

        if (this.reconnectEnabled) {
          this.reconnect();
        }
      });

      this.ws.on('error', (error) => {
        console.error('[AgentLink] WebSocket error:', error);
      });
    } catch (error: unknown) {
      console.error('[AgentLink] Failed to create WebSocket:', error);
      if (this.reconnectEnabled) {
        this.reconnect();
      }
    }
  }

  private reconnect(): void {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    this.reconnectAttempts++;

    console.log(`[AgentLink] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);

    setTimeout(() => {
      if (this.reconnectEnabled && this.onStateUpdateCallback) {
        this.connectWebSocket();
      }
    }, delay);
  }
}
