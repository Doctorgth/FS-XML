export type FileState = 'writable' | 'readonly' | 'unmarked';

export interface Project {
  id: number;
  name: string;
  root_dir: string;
  created_at: string;
}

export interface Profile {
  id: number;
  project_id: number;
  name: string;
  is_default: boolean;
}

export interface FileTreeNode {
  path: string;
  name: string;
  state: FileState;
}

export interface ExecutionResultItem {
  tag: string;
  success: boolean;
  target_path: string | null;
  message: string;
  details?: Record<string, any>;
}

export interface ExecutionResponse {
  session_id: number;
  status: string;
  total_commands: number;
  error_count: number;
  results: ExecutionResultItem[];
}

export interface HistorySession {
  id: number;
  created_at: string;
  status: string;
  total_commands: number;
  error_count: number;
  profile_name: string;
}

export interface ChangeRecord {
  id: number;
  session_id: number;
  command_tag: string;
  target_path: string | null;
  status: string;
  error_details: string | null;
  original_snapshot: string | null;
  new_snapshot: string | null;
}