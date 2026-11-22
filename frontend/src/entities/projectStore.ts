import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../shared/api/client';
import type { FileTreeNode, HistorySession, Profile, Project } from '../shared/api/types';

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const profiles = ref<Profile[]>([]);
  const currentProfile = ref<Profile | null>(null);
  const files = ref<FileTreeNode[]>([]);
  const history = ref<HistorySession[]>([]);
  const loading = ref(false);

  async function loadProjects() {
    projects.value = await api.getProjects();
    if (!currentProject.value && projects.value.length > 0) {
      await selectProject(projects.value[0]);
    }
  }

  async function selectProject(proj: Project) {
    currentProject.value = proj;
    profiles.value = await api.getProfiles(proj.id);
    const def = profiles.value.find((p) => p.is_default) || profiles.value[0];
    if (def) {
      await selectProfile(def);
    }
    await loadHistory();
  }

  async function selectProfile(prof: Profile) {
    currentProfile.value = prof;
    if (currentProject.value) {
      files.value = await api.getFiles(currentProject.value.id, prof.id);
    }
  }

  async function addProject(name: string, root_dir: string) {
    const proj = await api.createProject(name, root_dir);
    await loadProjects();
    await selectProject(proj);
  }

  async function removeProject(id: number) {
    await api.deleteProject(id);
    if (currentProject.value?.id === id) {
      currentProject.value = null;
      currentProfile.value = null;
      profiles.value = [];
      files.value = [];
      history.value = [];
    }
    await loadProjects();
  }

  async function updateProjectDirectory(id: number, new_dir: string) {
    await api.updateProjectDir(id, new_dir);
    if (currentProject.value && currentProject.value.id === id) {
      currentProject.value.root_dir = new_dir;
      if (currentProfile.value) {
        files.value = await api.getFiles(id, currentProfile.value.id);
      }
    }
  }

  const systemLogs = ref<string[]>([]);

  function addLog(msg: string) {
    const time = new Date().toLocaleTimeString();
    systemLogs.value.unshift(`[${time}] ${msg}`);
    if (systemLogs.value.length > 100) systemLogs.value.pop();
  }

  async function addProfile(name: string) {
    if (!currentProject.value) return;
    const prof = await api.createProfile(currentProject.value.id, name);
    profiles.value = await api.getProfiles(currentProject.value.id);
    await selectProfile(prof);
    addLog(`Создан профиль: ${name}`);
  }

  async function removeProfile(profileId: number) {
    if (!currentProject.value) return;
    await api.deleteProfile(profileId);
    profiles.value = await api.getProfiles(currentProject.value.id);
    const def = profiles.value.find((p) => p.is_default) || profiles.value[0];
    if (def) await selectProfile(def);
    addLog('Профиль удален');
  }

  async function updateFileState(rel_path: string, state: 'writable' | 'readonly' | 'unmarked') {
    if (!currentProfile.value) return;
    await api.updateFileRule(currentProfile.value.id, rel_path, state);
    const item = files.value.find((f) => f.path === rel_path);
    if (item) {
      item.state = state;
    }
  }

  async function updateFilesStateBulk(paths: string[], state: 'writable' | 'readonly' | 'unmarked') {
    if (!currentProfile.value || paths.length === 0) return;
    const payload = paths.map((rel_path) => ({ rel_path, state }));
    await api.updateFileRulesBulk(currentProfile.value.id, payload);
    const pathSet = new Set(paths);
    for (const item of files.value) {
      if (pathSet.has(item.path)) {
        item.state = state;
      }
    }
  }

  async function loadHistory() {
    if (!currentProject.value) return;
    history.value = await api.getHistory(currentProject.value.id);
  }

  return {
    projects,
    currentProject,
    profiles,
    currentProfile,
    files,
    history,
    loading,
    loadProjects,
    selectProject,
    selectProfile,
    addProject,
    removeProject,
    addProfile,
    updateFileState,
    updateFilesStateBulk,
    loadHistory,
    updateProjectDirectory,
    removeProfile,
    systemLogs,
    addLog,
  };
});