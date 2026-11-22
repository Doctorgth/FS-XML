import type {
  ChangeRecord,
  ExecutionResponse,
  FileTreeNode,
  HistorySession,
  Profile,
  Project,
} from './types';

const BASE_URL = 'http://127.0.0.1:18420/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  getProjects: () => request<Project[]>('/projects'),
  createProject: (name: string, root_dir: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, root_dir }),
    }),
  deleteProject: (id: number) =>
    request<{ success: boolean }>(`/projects/${id}`, { method: 'DELETE' }),
  updateProjectDir: (id: number, root_dir: string) =>
    request<{ success: boolean; root_dir: string }>(`/projects/${id}/directory`, {
      method: 'PUT',
      body: JSON.stringify({ root_dir }),
    }),
  selectFolderDialog: () =>
    request<{ folder: string | null; error?: string }>('/system/select-folder', {
      method: 'POST',
    }),
  openProjectFolder: (projectId: number) =>
    request<{ success: boolean }>(`/projects/${projectId}/open-folder`, {
      method: 'POST',
    }),
  saveProjectConfig: (projectId: number) =>
    request<{ success: boolean; config_path: string }>(`/projects/${projectId}/config/save`, {
      method: 'POST',
    }),
  selectConfigFile: () =>
    request<{ file_path: string | null; error?: string }>('/system/select-config-file', {
      method: 'POST',
    }),
  importProjectConfig: (config_path: string, root_dir?: string) =>
    request<{ success: boolean; project: Project; imported_profiles: number; imported_rules: number }>(
      '/projects/import-config',
      {
        method: 'POST',
        body: JSON.stringify({ config_path, root_dir }),
      }
    ),

  getProfiles: (projectId: number) => request<Profile[]>(`/projects/${projectId}/profiles`),
  createProfile: (projectId: number, name: string) =>
    request<Profile>(`/projects/${projectId}/profiles`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  deleteProfile: (profileId: number) =>
    request<{ success: boolean }>(`/profiles/${profileId}`, { method: 'DELETE' }),

  getFiles: (projectId: number, profileId: number) =>
    request<FileTreeNode[]>(`/profiles/${profileId}/files?project_id=${projectId}`),
  updateFileRule: (profileId: number, rel_path: string, state: string) =>
    request<{ success: boolean }>(`/profiles/${profileId}/files`, {
      method: 'POST',
      body: JSON.stringify({ rel_path, state }),
    }),
  updateFileRulesBulk: (profileId: number, rules: Array<{ rel_path: string; state: string }>) =>
    request<{ success: boolean; updated: number }>(`/profiles/${profileId}/files/bulk`, {
      method: 'POST',
      body: JSON.stringify({ rules }),
    }),

  getDump: (projectId: number, profileId: number, includeUnmarked: boolean, ignoreTests: boolean = false) =>
    request<{ dump: string; dump_path?: string }>(
      `/projects/${projectId}/dump?profile_id=${profileId}&include_unmarked=${includeUnmarked}&ignore_tests=${ignoreTests}`
    ),

  executeXml: (projectId: number, profileId: number, xml_content: string, allow_management: boolean) =>
    request<ExecutionResponse>(`/projects/${projectId}/execute?profile_id=${profileId}`, {
      method: 'POST',
      body: JSON.stringify({ xml_content, allow_management }),
    }),

  getHistory: (projectId: number) => request<HistorySession[]>(`/projects/${projectId}/history`),
  getSessionDetails: (sessionId: number) => request<ChangeRecord[]>(`/sessions/${sessionId}`),
  clearHistory: (projectId: number) =>
    request<{ success: boolean }>(`/projects/${projectId}/history`, { method: 'DELETE' }),

  getSystemPrompt: () => request<{ prompt: string }>('/prompt'),

  getBackgroundSetting: () =>
    request<{ filename: string; background_url: string; enabled: boolean }>('/settings/background'),
  toggleBackground: (enabled: boolean) =>
    request<{ success: boolean; enabled: boolean }>(`/settings/background/toggle?enabled=${enabled}`, {
      method: 'PUT',
    }),
  selectBackgroundImage: () =>
    request<{ selected: boolean; filename: string | null; background_url: string | null }>(
      '/settings/background/select',
      { method: 'POST' }
    ),

  getGlobalIgnore: () => request<{ content: string }>('/ignore/global'),
  saveGlobalIgnore: (content: string) =>
    request<{ success: boolean }>('/ignore/global', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  getProjectIgnore: (projectId: number) =>
    request<{ content: string }>(`/projects/${projectId}/ignore/project`),
  saveProjectIgnore: (projectId: number, content: string) =>
    request<{ success: boolean }>(`/projects/${projectId}/ignore/project`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  rollbackRecord: (recordId: number, force: boolean) =>
    request<{ success: boolean; manual_edited: boolean; message?: string }>(`/records/${recordId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ force }),
    }),
  reapplyRecord: (recordId: number) =>
    request<{ success: boolean }>(`/records/${recordId}/reapply`, {
      method: 'POST',
    }),
  getFileContent: (projectId: number, rel_path: string) =>
    request<{ content: string; is_binary: boolean }>(
      `/projects/${projectId}/file-content?rel_path=${encodeURIComponent(rel_path)}`
    ),

  getSnapshots: (projectId: number) =>
    request<Array<{ id: number; name: string; created_at: string; profile_name: string | null }>>(
      `/projects/${projectId}/snapshots`
    ),
  createSnapshot: (projectId: number, profileId: number, name: string, for_all_profiles: boolean) =>
    request<{ success: boolean; id: number }>(`/projects/${projectId}/snapshots?profile_id=${profileId}`, {
      method: 'POST',
      body: JSON.stringify({ name, for_all_profiles }),
    }),
  restoreSnapshot: (snapshotId: number) =>
    request<{ success: boolean }>(`/snapshots/${snapshotId}/restore`, {
      method: 'POST',
    }),
  deleteSnapshot: (snapshotId: number) =>
    request<{ success: boolean }>(`/snapshots/${snapshotId}`, {
      method: 'DELETE',
    }),
};