// AgentLink API Types

export interface AgentState {
  id: string;
  agent_id: string;
  timestamp: string;
  task: Task;
  context: Context;
  knowledge: Knowledge;
  working_memory: WorkingMemory;
  handoff: Handoff | null;
}

export interface Task {
  type: 'bug_fix' | 'feature' | 'review' | 'research' | 'refactor';
  description: string;
  priority: number; // 1-5
  status: 'pending' | 'in_progress' | 'blocked' | 'done';
}

export interface Context {
  files: FileContext[];
  git: GitContext | null;
  errors: ErrorContext[];
}

export interface FileContext {
  path: string;
  diff?: string;
  lines?: [number, number];
  hash?: string;
}

export interface GitContext {
  repo: string;
  branch: string;
  commit: string;
}

export interface ErrorContext {
  type: string;
  message: string;
  stack?: string;
}

export interface Knowledge {
  amem_ids: string[];
  qmd_refs: string[];
  external_urls: string[];
}

export interface WorkingMemory {
  hypotheses: string[];
  open_questions: string[];
  decisions: Decision[];
  findings: string[];
}

export interface Decision {
  what: string;
  why: string;
  when: string;
}

export interface Handoff {
  to_agent: string | null;
  reason: string | null;
  required_skills: string[];
}

// Analytics & Stats Types

export interface Stats {
  total_states: number;
  unique_agents: number;
  total_handoffs: number;
  task_types: Record<string, number>;
  statuses: Record<string, number>;
  active_ws_connections: number;
  timestamp: string;
}

export interface Analytics {
  time_window_hours: number;
  since: string;
  states_over_time: TimeSeriesPoint[];
  handoffs_over_time: TimeSeriesPoint[];
  activity_by_agent: AgentActivity[];
  timestamp: string;
}

export interface TimeSeriesPoint {
  hour: string;
  count: number;
}

export interface AgentActivity {
  agent_id: string;
  count: number;
}

export interface ActiveAgent {
  agent_id: string;
  connections: number;
  channel: string;
}

export interface ActiveAgentsResponse {
  active_agents: ActiveAgent[];
  total_broadcast_listeners: number;
  timestamp: string;
}

// WebSocket Message Types

export type WSMessage =
  | WSConnectedMessage
  | WSSubscribedMessage
  | WSUnsubscribedMessage
  | WSStateCreatedMessage
  | WSHandoffReceivedMessage
  | WSErrorMessage;

export interface WSConnectedMessage {
  type: 'connected';
  channel: string;
  timestamp: string;
}

export interface WSSubscribedMessage {
  type: 'subscribed';
  channel: string;
  timestamp: string;
}

export interface WSUnsubscribedMessage {
  type: 'unsubscribed';
  timestamp: string;
}

export interface WSStateCreatedMessage {
  type: 'state_created';
  state_id: string;
  from_agent: string;
  timestamp: string;
  task_type: string;
  task_status: string;
}

export interface WSHandoffReceivedMessage {
  type: 'handoff_received';
  state_id: string;
  from_agent: string;
  to_agent: string;
  reason: string;
  timestamp: string;
}

export interface WSErrorMessage {
  type: 'error';
  message: string;
}
