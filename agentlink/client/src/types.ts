/**
 * AgentLink TypeScript Types
 * Auto-generated from backend schema
 */

export interface FileContext {
  path: string;
  diff?: string | null;
  lines?: [number, number] | null;
  hash?: string | null;
}

export interface GitContext {
  repo: string;
  branch: string;
  commit: string;
}

export interface ErrorContext {
  type: string;
  message: string;
  stack?: string | null;
}

export interface Context {
  files?: FileContext[];
  git?: GitContext | null;
  errors?: ErrorContext[];
}

export interface Knowledge {
  amem_ids?: string[];
  qmd_refs?: string[];
  external_urls?: string[];
}

export interface Decision {
  what: string;
  why: string;
  when: string; // ISO 8601 timestamp
}

export interface WorkingMemory {
  hypotheses?: string[];
  open_questions?: string[];
  decisions?: Decision[];
  findings?: string[];
}

export interface Task {
  type: 'bug_fix' | 'feature' | 'review' | 'research' | 'refactor';
  description: string;
  priority: 1 | 2 | 3 | 4 | 5;
  status?: 'pending' | 'in_progress' | 'blocked' | 'done';
}

export interface Handoff {
  to_agent?: string | null;
  reason?: string | null;
  required_skills?: string[];
}

export interface AgentState {
  id: string;
  agent_id: string;
  timestamp: string; // ISO 8601
  task: Task;
  context: Context;
  knowledge?: Knowledge;
  working_memory?: WorkingMemory;
  handoff?: Handoff | null;
}

export interface StateFilter {
  agent_id?: string;
  status?: string;
  limit?: number;
}

export interface HealthResponse {
  status: string;
  states_count: number;
  timestamp: string;
}
