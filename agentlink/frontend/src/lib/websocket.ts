// AgentLink WebSocket Client

import type { WSMessage } from '../types/api';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://192.168.178.102:8000/ws';

export type WSEventHandler = (message: WSMessage) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 32000;
  private handlers: Set<WSEventHandler> = new Set();
  private currentChannel = 'all';
  private autoReconnect: boolean;
  private subscriberCount = 0; // Track active subscribers

  constructor(autoReconnect = true) {
    this.autoReconnect = autoReconnect;
  }

  connect(channel: string = 'all'): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(WS_URL);
        this.currentChannel = channel;

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectDelay = 1000; // Reset reconnect delay

          // Subscribe to channel if not default
          if (channel !== 'all') {
            this.subscribe(channel);
          }

          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            this.notifyHandlers(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          if (this.autoReconnect) {
            this.scheduleReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.autoReconnect = false;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(channel: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: 'subscribe',
          channel,
        })
      );
      this.currentChannel = channel;
    }
  }

  unsubscribe(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: 'unsubscribe',
        })
      );
    }
  }

  on(handler: WSEventHandler): () => void {
    this.handlers.add(handler);
    this.subscriberCount++;
    
    // Return unsubscribe function
    return () => {
      this.handlers.delete(handler);
      this.subscriberCount--;
      
      // Auto-disconnect if no subscribers left
      if (this.subscriberCount === 0 && this.ws) {
        console.log('No subscribers left, disconnecting WebSocket');
        this.disconnect();
      }
    };
  }

  private notifyHandlers(message: WSMessage): void {
    this.handlers.forEach((handler) => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in WebSocket handler:', error);
      }
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) return;

    console.log(`Reconnecting in ${this.reconnectDelay}ms...`);

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect(this.currentChannel).catch(() => {
        // Exponential backoff
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          this.maxReconnectDelay
        );
        // Retry connection after backoff
        this.scheduleReconnect();
      });
    }, this.reconnectDelay);
  }

  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  get channel(): string {
    return this.currentChannel;
  }
}

// Singleton instance
export const wsClient = new WebSocketClient();
