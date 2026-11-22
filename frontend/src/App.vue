<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useProjectStore } from './entities/projectStore';
import { api } from './shared/api/client';
import ExecutionHub from './widgets/ExecutionHub/ExecutionHub.vue';
import FileTreeModal from './widgets/FileTree/FileTreeModal.vue';
import HistoryPanel from './widgets/HistoryPanel/HistoryPanel.vue';
import CreateSnapshotModal from './widgets/CreateSnapshotModal.vue';
import SnapshotsListModal from './widgets/SnapshotsListModal.vue';
import SnapshotHelpModal from './widgets/SnapshotHelpModal.vue';
import ConfigHelpModal from './widgets/ConfigHelpModal.vue';
import InstructionModal from './widgets/InstructionModal.vue';
import AttachedFilesViewerModal from './widgets/AttachedFilesViewerModal.vue';
import { nextTick, watch } from 'vue';

const store = useProjectStore();
const showViewModal = ref(false);
const newProjectNameInput = ref<HTMLInputElement | null>(null);
const newProfileNameInput = ref<HTMLInputElement | null>(null);
const execHubRef = ref<any>(null);

const showFileModal = ref(false);
const showNewProjectModal = ref(false);
const newProjName = ref('');
const newProjDir = ref('');
const projectCreateError = ref('');

// Модалка создания профиля
const showNewProfileModal = ref(false);
const newProfileName = ref('');

// Модалки списка профилей и подтверждения удаления профиля
const showProfilesListModal = ref(false);
const showDeleteProfileModal = ref(false);
const profileToDelete = ref<{ id: number; name: string } | null>(null);

// Модалки снапшотов и конфигурации
const showCreateSnapshotModal = ref(false);
const showSnapshotsListModal = ref(false);
const showSnapshotHelpModal = ref(false);
const showConfigHelpModal = ref(false);
const showInstructionModal = ref(false);
const isLeftPanelCollapsed = ref(false);
const isLogsCollapsed = ref(true);
const openMenu = ref<'profile' | 'snapshots' | 'config' | 'personalization' | null>(null);
const executionStatus = ref<'idle' | 'success' | 'error'>('idle');
const backgroundUrl = ref('http://127.0.0.1:18420/images/background.png');
const isBackgroundEnabled = ref(true);

const notificationModal = ref<{
  title: string;
  message: string;
  highlightPath?: string;
  type: 'success' | 'error';
} | null>(null);

async function handleOpenProjectFolder() {
  if (!store.currentProject) return;
  try {
    await api.openProjectFolder(store.currentProject.id);
    store.addLog(`Открыта папка проекта: ${store.currentProject.root_dir}`);
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка открытия папки',
      message: err.message || 'Не удалось открыть папку проекта.',
      type: 'error',
    };
  }
}

async function handleSaveConfig() {
  if (!store.currentProject) return;
  try {
    const res = await api.saveProjectConfig(store.currentProject.id);
    store.addLog(`Конфигурация сохранена: ${res.config_path}`);
    notificationModal.value = {
      title: 'Конфигурация сохранена',
      message: 'Файл конфигурации с профилями и правами на файлы успешно сохранен в корневую папку проекта:',
      highlightPath: res.config_path,
      type: 'success',
    };
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка сохранения конфигурации',
      message: err.message || 'Не удалось сохранить конфигурацию.',
      type: 'error',
    };
  }
}

async function handleLoadConfig() {
  try {
    const fileRes = await api.selectConfigFile();
    if (fileRes.error) {
      throw new Error(fileRes.error);
    }
    if (!fileRes.file_path) return;

    const impRes = await api.importProjectConfig(fileRes.file_path);
    await store.loadProjects();
    const targetProj = store.projects.find((p) => p.id === impRes.project.id) || impRes.project;
    await store.selectProject(targetProj);
    store.addLog(
      `Загружена конфигурация (${impRes.imported_profiles} профилей, ${impRes.imported_rules} прав)`
    );
    notificationModal.value = {
      title: 'Конфигурация загружена',
      message: `Проект "${targetProj.name}" успешно обновлен! Импортировано профилей: ${impRes.imported_profiles}, правил файлов: ${impRes.imported_rules}.`,
      type: 'success',
    };
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка загрузки конфигурации',
      message: err.message || 'Не удалось загрузить конфигурацию.',
      type: 'error',
    };
  }
}

async function handleSnapshotRestored() {
  if (!store.currentProject) return;
  const prevProfileName = store.currentProfile?.name;
  await store.selectProject(store.currentProject);
  if (prevProfileName) {
    const restoredProf = store.profiles.find((p) => p.name === prevProfileName);
    if (restoredProf) {
      await store.selectProfile(restoredProf);
    }
  }
}

async function handleCreateSnapshot(payload: { name: string; forAll: boolean }) {
  if (!store.currentProject || !store.currentProfile) return;
  try {
    await api.createSnapshot(store.currentProject.id, store.currentProfile.id, payload.name, payload.forAll);
    store.addLog(`Создан снапшот: ${payload.name}`);
    showCreateSnapshotModal.value = false;
    notificationModal.value = {
      title: 'Снапшот создан',
      message: `Снапшот "${payload.name}" успешно сохранен.`,
      type: 'success',
    };
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка создания снапшота',
      message: err.message || 'Не удалось создать снапшот.',
      type: 'error',
    };
  }
}

const allowManagement = ref(false);
const includeUnmarked = ref(false);
const ignoreTests = ref(false);

// Ресайз боковых панелей (мышкой)
const leftWidth = ref(260);
const rightWidth = ref(320);

let isResizingLeft = false;
let isResizingRight = false;

function startResizeLeft() {
  isResizingLeft = true;
  window.addEventListener('mousemove', handleMouseMove);
  window.addEventListener('mouseup', stopResize);
}

function startResizeRight() {
  isResizingRight = true;
  window.addEventListener('mousemove', handleMouseMove);
  window.addEventListener('mouseup', stopResize);
}

function handleMouseMove(e: MouseEvent) {
  if (isResizingLeft) {
    if (e.clientX > 180 && e.clientX < 500) {
      leftWidth.value = e.clientX;
    }
  } else if (isResizingRight) {
    const fromRight = window.innerWidth - e.clientX;
    if (fromRight > 240 && fromRight < 600) {
      rightWidth.value = fromRight;
    }
  }
}

function stopResize() {
  isResizingLeft = false;
  isResizingRight = false;
  window.removeEventListener('mousemove', handleMouseMove);
  window.removeEventListener('mouseup', stopResize);
}

watch(showNewProjectModal, async (val) => {
  if (val) {
    await nextTick();
    newProjectNameInput.value?.focus();
  }
});

watch(showNewProfileModal, async (val) => {
  if (val) {
    await nextTick();
    newProfileNameInput.value?.focus();
  }
});

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showDeleteProfileModal.value) {
      showDeleteProfileModal.value = false;
      return;
    }
    showProfilesListModal.value = false;
    showNewProjectModal.value = false;
    showNewProfileModal.value = false;
    showFileModal.value = false;
    showViewModal.value = false;
    showInstructionModal.value = false;
    notificationModal.value = null;
  }
}

async function loadBackgroundSetting() {
  try {
    const res = await api.getBackgroundSetting();
    if (res?.background_url) {
      backgroundUrl.value = `http://127.0.0.1:18420${res.background_url}`;
    }
    if (typeof res?.enabled === 'boolean') {
      isBackgroundEnabled.value = res.enabled;
    }
  } catch {
    // fallback to default background.png
  }
}

async function handleToggleBackground(enabled: boolean) {
  isBackgroundEnabled.value = enabled;
  try {
    await api.toggleBackground(enabled);
    store.addLog(enabled ? 'Фоновое изображение включено.' : 'Фоновое изображение отключено.');
  } catch {
    // fallback
  }
}

async function handleChangeBackground() {
  openMenu.value = null;
  try {
    const res = await api.selectBackgroundImage();
    if (res.selected && res.background_url) {
      backgroundUrl.value = `http://127.0.0.1:18420${res.background_url}?t=${Date.now()}`;
      store.addLog(`Фоновое изображение изменено: ${res.filename}`);
    }
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка смены фона',
      message: err.message || 'Не удалось изменить фоновое изображение.',
      type: 'error',
    };
  }
}

onMounted(() => {
  store.loadProjects();
  loadBackgroundSetting();
  store.addLog('Приложение запущено.');
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

async function handleBrowseFolderForNew() {
  try {
    const res = await api.selectFolderDialog();
    if (res.error) {
      projectCreateError.value = res.error;
      return;
    }
    if (res.folder) {
      newProjDir.value = res.folder;
      if (!newProjName.value.trim()) {
        const parts = res.folder.replace(/\\/g, '/').split('/');
        newProjName.value = parts[parts.length - 1] || 'New Project';
      }
    }
  } catch (err: any) {
    projectCreateError.value = err.message || 'Не удалось открыть диалог выбора папки';
  }
}

async function handleChangeProjectDir() {
  if (!store.currentProject) return;
  try {
    const res = await api.selectFolderDialog();
    if (res.error) {
      throw new Error(res.error);
    }
    if (res.folder) {
      await store.updateProjectDirectory(store.currentProject.id, res.folder);
      store.addLog(`Директория проекта изменена на: ${res.folder}`);
    }
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка изменения директории',
      message: err.message || 'Не удалось изменить директорию проекта.',
      type: 'error',
    };
  }
}

async function handleCreateProject() {
  projectCreateError.value = '';
  if (!newProjName.value.trim()) {
    projectCreateError.value = 'Введите название проекта';
    return;
  }
  if (!newProjDir.value.trim()) {
    projectCreateError.value = 'Укажите папку проекта';
    return;
  }
  try {
    await store.addProject(newProjName.value.trim(), newProjDir.value.trim());
    store.addLog(`Создан проект: ${newProjName.value}`);
    newProjName.value = '';
    newProjDir.value = '';
    showNewProjectModal.value = false;
  } catch (err: any) {
    projectCreateError.value = err.message || 'Ошибка создания проекта';
  }
}

async function handleCreateProfile() {
  if (!newProfileName.value.trim()) return;
  try {
    await store.addProfile(newProfileName.value.trim());
    newProfileName.value = '';
    showNewProfileModal.value = false;
  } catch (err: any) {
    notificationModal.value = {
      title: 'Ошибка создания профиля',
      message: err.message || 'Не удалось создать профиль.',
      type: 'error',
    };
  }
}

function askDeleteProfile(prof: { id: number; name: string }) {
  profileToDelete.value = prof;
  showDeleteProfileModal.value = true;
}

async function confirmDeleteProfile() {
  if (!profileToDelete.value) return;
  await store.removeProfile(profileToDelete.value.id);
  showDeleteProfileModal.value = false;
  profileToDelete.value = null;
}
</script>

<template>
  <div
    class="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-200 font-sans select-none bg-cover bg-center bg-no-repeat"
    :style="isBackgroundEnabled ? { backgroundImage: `url('${backgroundUrl}')` } : {}"
  >
    <!-- 1. ЛЕВАЯ ПАНЕЛЬ: Свернутое состояние -->
    <div
      v-if="isLeftPanelCollapsed"
      class="w-9 flex flex-col items-center pt-2.5 bg-slate-950/45 border-r border-slate-800/60 shrink-0"
    >
      <button
        @click="isLeftPanelCollapsed = false"
        class="w-6 h-6 flex items-center justify-center rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/70 text-xs transition"
        title="Развернуть левую панель"
      >
        ▶
      </button>
    </div>

    <!-- 1. ЛЕВАЯ ПАНЕЛЬ: Проекты + Лог работы -->
    <div
      v-else
      :style="{ width: `${leftWidth}px` }"
      class="flex flex-col bg-slate-950/45 border-r border-slate-800/60 shrink-0"
    >
      <div class="p-3 border-b border-slate-800/60">
        <div class="flex items-center justify-between gap-2">
          <h1 class="text-xs font-bold tracking-wider text-sky-400 uppercase">AI INTERPRETER</h1>
          <button
            @click="isLeftPanelCollapsed = true"
            class="w-5 h-5 flex items-center justify-center rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 text-[10px] transition"
            title="Свернуть левую панель"
          >
            ◀
          </button>
        </div>
        <button
          @click="showNewProjectModal = true"
          class="w-full mt-2.5 bg-sky-600 hover:bg-sky-500 text-white font-medium py-1.5 px-3 rounded text-xs transition shadow"
        >
          + Новый проект
        </button>
      </div>

      <!-- Список проектов -->
      <div class="p-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Проекты:</div>
      <div class="flex-1 overflow-y-auto px-2 space-y-1">
        <div
          v-for="proj in store.projects"
          :key="proj.id"
          @click="store.selectProject(proj); store.addLog(`Выбран проект: ${proj.name}`)"
          :class="store.currentProject?.id === proj.id ? 'bg-sky-950/60 border-sky-800 text-white' : 'border-transparent text-slate-400 hover:bg-slate-900'"
          class="flex justify-between items-center px-2.5 py-1.5 border rounded cursor-pointer transition text-xs"
        >
          <span class="font-medium truncate mr-2">{{ proj.name }}</span>
          <button
            @click.stop="store.removeProject(proj.id); store.addLog(`Удален проект: ${proj.name}`)"
            class="text-slate-500 hover:text-rose-400 px-1 text-xs transition"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- Блок автора и ссылок над логами работы -->
      <div class="border-t border-slate-800/60 p-2.5 flex flex-col gap-2">
        <div class="grid grid-cols-2 gap-1.5">
          <a
            href="https://github.com/Doctorgth/FS-XML"
            target="_blank"
            rel="noopener noreferrer"
            class="bg-sky-500/20 hover:bg-sky-500/35 border border-sky-500/40 text-sky-300 hover:text-sky-200 text-[11px] font-medium py-1.5 px-2 rounded text-center transition flex items-center justify-center"
          >
            GitHub
          </a>
          <a
            href="https://boosty.to/doctorgth"
            target="_blank"
            rel="noopener noreferrer"
            class="bg-orange-500/20 hover:bg-orange-500/35 border border-orange-500/40 text-orange-300 hover:text-orange-200 text-[11px] font-medium py-1.5 px-2 rounded text-center transition flex items-center justify-center"
          >
            Boosty
          </a>
        </div>
        <div class="text-left text-[10px] text-slate-400 font-mono">
          © Doctorgth 2026
        </div>
      </div>

      <!-- Нижний блок левой панели: Лог работы (сворачивается вниз, по умолчанию свернут) -->
      <div
        :class="isLogsCollapsed ? 'py-1.5 px-2.5' : 'h-48 p-2.5'"
        class="border-t border-slate-800/60 flex flex-col transition-all"
      >
        <div class="flex justify-between items-center" :class="isLogsCollapsed ? '' : 'mb-1.5'">
          <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Лог работы{{ isLogsCollapsed && store.systemLogs.length > 0 ? ` (${store.systemLogs.length})` : ':' }}
          </span>
          <div class="flex items-center gap-1">
            <button
              v-if="!isLogsCollapsed"
              @click="store.systemLogs = []"
              class="text-[10px] text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded bg-slate-800/80 hover:bg-slate-700 transition"
            >
              Очистить
            </button>
            <button
              @click="isLogsCollapsed = !isLogsCollapsed"
              class="w-5 h-5 flex items-center justify-center rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/70 text-[10px] transition"
              :title="isLogsCollapsed ? 'Развернуть лог работы' : 'Свернуть лог работы'"
            >
              {{ isLogsCollapsed ? '▲' : '▼' }}
            </button>
          </div>
        </div>
        <div
          v-if="!isLogsCollapsed"
          class="flex-1 overflow-y-auto font-mono text-[10px] text-slate-400 space-y-1 pr-1 select-text"
        >
          <div v-for="(log, i) in store.systemLogs" :key="i" class="leading-tight">
            {{ log }}
          </div>
        </div>
      </div>
    </div>

    <!-- СПЛИТТЕР РЕСАЙЗА СЛЕВА -->
    <div
      v-if="!isLeftPanelCollapsed"
      @mousedown="startResizeLeft"
      class="w-1 bg-slate-800/40 hover:bg-sky-500 cursor-col-resize transition shrink-0"
    ></div>

    <!-- 2. ЦЕНТРАЛЬНАЯ ОБЛАСТЬ -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Верхняя панель Строка 1: Компактное IDE-меню (разворачивается при наведении) -->
      <div class="px-2.5 py-0.5 border-b border-slate-800/60 bg-slate-950/50 flex items-center gap-1 text-[11px] relative z-30">
        <!-- Меню: Профиль -->
        <div
          class="relative"
          @mouseenter="openMenu = 'profile'"
          @mouseleave="openMenu = null"
        >
          <button
            @click="openMenu = 'profile'"
            :class="openMenu === 'profile' ? 'bg-slate-800/90 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'"
            class="px-2 py-0.5 rounded transition font-medium"
          >
            Профиль
          </button>
          <div
            v-show="openMenu === 'profile'"
            class="absolute left-0 top-full pt-0.5 w-48 z-40"
          >
            <div class="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1">
              <button
                :disabled="!store.currentProject"
                @click="openMenu = null; showNewProfileModal = true"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-sky-600/30 hover:text-white disabled:opacity-40 transition flex items-center gap-2"
              >
                <span>+</span>
                <span>Новый профиль</span>
              </button>
              <button
                :disabled="!store.currentProject"
                @click="openMenu = null; showProfilesListModal = true"
                class="w-full text-left px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-600/30 hover:text-rose-200 disabled:opacity-40 transition flex items-center gap-2"
              >
                <span>✕</span>
                <span>Удалить профиль</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Меню: Снапшоты -->
        <div
          class="relative"
          @mouseenter="openMenu = 'snapshots'"
          @mouseleave="openMenu = null"
        >
          <button
            @click="openMenu = 'snapshots'"
            :class="openMenu === 'snapshots' ? 'bg-slate-800/90 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'"
            class="px-2 py-0.5 rounded transition font-medium"
          >
            Снапшоты
          </button>
          <div
            v-show="openMenu === 'snapshots'"
            class="absolute left-0 top-full pt-0.5 w-52 z-40"
          >
            <div class="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1">
              <button
                :disabled="!store.currentProject"
                @click="openMenu = null; showCreateSnapshotModal = true"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-sky-600/30 hover:text-white disabled:opacity-40 transition flex items-center gap-2"
              >
                <span>📸</span>
                <span>Создать снапшот</span>
              </button>
              <button
                :disabled="!store.currentProject"
                @click="openMenu = null; showSnapshotsListModal = true"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-sky-600/30 hover:text-white disabled:opacity-40 transition flex items-center gap-2"
              >
                <span>📂</span>
                <span>Загрузить снапшот</span>
              </button>
              <div class="my-1 border-t border-slate-800"></div>
              <button
                @click="openMenu = null; showSnapshotHelpModal = true"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-amber-300 transition flex items-center gap-2"
              >
                <span>💡</span>
                <span>Что такое снапшот?</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Меню: Конфигурация -->
        <div
          class="relative"
          @mouseenter="openMenu = 'config'"
          @mouseleave="openMenu = null"
        >
          <button
            @click="openMenu = 'config'"
            :class="openMenu === 'config' ? 'bg-slate-800/90 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'"
            class="px-2 py-0.5 rounded transition font-medium"
          >
            Конфигурация
          </button>
          <div
            v-show="openMenu === 'config'"
            class="absolute left-0 top-full pt-0.5 w-56 z-40"
          >
            <div class="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1">
              <button
                :disabled="!store.currentProject"
                @click="openMenu = null; handleSaveConfig()"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-sky-600/30 hover:text-white disabled:opacity-40 transition flex items-center gap-2"
              >
                <span>💾</span>
                <span>Сохранить конфигурацию</span>
              </button>
              <button
                @click="openMenu = null; handleLoadConfig()"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-sky-600/30 hover:text-white transition flex items-center gap-2"
              >
                <span>📥</span>
                <span>Загрузить конфигурацию</span>
              </button>
              <div class="my-1 border-t border-slate-800"></div>
              <button
                @click="openMenu = null; showConfigHelpModal = true"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-sky-300 transition flex items-center gap-2"
              >
                <span>⚙</span>
                <span>Что такое конфигурация?</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Меню: Персонализация -->
        <div
          class="relative"
          @mouseenter="openMenu = 'personalization'"
          @mouseleave="openMenu = null"
        >
          <button
            @click="openMenu = 'personalization'"
            :class="openMenu === 'personalization' ? 'bg-slate-800/90 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'"
            class="px-2 py-0.5 rounded transition font-medium"
          >
            Персонализация
          </button>
          <div
            v-show="openMenu === 'personalization'"
            class="absolute left-0 top-full pt-0.5 w-52 z-40"
          >
            <div class="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1">
              <label class="w-full px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 transition flex items-center justify-between cursor-pointer select-none">
                <span>Отображать фон</span>
                <input
                  type="checkbox"
                  :checked="isBackgroundEnabled"
                  @change="handleToggleBackground(($event.target as HTMLInputElement).checked)"
                  class="accent-sky-500 rounded cursor-pointer"
                />
              </label>
              <div class="my-1 border-t border-slate-800"></div>
              <button
                @click="handleChangeBackground"
                class="w-full text-left px-3 py-1.5 text-xs text-slate-200 hover:bg-sky-600/30 hover:text-white transition flex items-center gap-2"
              >
                <span>🖼</span>
                <span>Изменить фон</span>
              </button>
            </div>
          </div>
        </div>

        <span class="text-slate-700 mx-0.5">|</span>

        <!-- Кнопка открытия папки проекта в верхней панели -->
        <button
          :disabled="!store.currentProject"
          @click="handleOpenProjectFolder"
          class="px-2 py-0.5 rounded transition font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 disabled:opacity-40"
          title="Открыть корневую папку проекта в проводнике"
        >
          Папка проекта
        </button>

        <span class="text-slate-700 mx-0.5">|</span>

        <!-- Кнопка Инструкция -->
        <button
          @click="openMenu = null; showInstructionModal = true"
          class="px-2 py-0.5 rounded transition font-medium text-slate-300 hover:text-white hover:bg-slate-800/60"
          title="Открыть инструкцию по использованию программы"
        >
          Инструкция
        </button>
      </div>

      <!-- Верхняя панель Строка 2: Проект, Директория и Вкладки профилей -->
      <div class="px-3 py-1 border-b border-slate-800/60 bg-slate-950/40 flex flex-wrap gap-2 items-center justify-between text-[11px]">
        <div class="flex flex-wrap items-center gap-1.5 min-w-0">
          <span class="text-slate-400 font-bold">Проект:</span>
          <span class="text-white font-bold">{{ store.currentProject?.name || '-' }}</span>
          <span class="text-slate-600">|</span>
          <span class="text-slate-400">Директория:</span>
          <span class="text-slate-300 font-mono text-[11px] truncate max-w-xs">{{ store.currentProject?.root_dir || 'Не выбрана' }}</span>

          <button
            v-if="store.currentProject"
            @click="handleChangeProjectDir"
            class="bg-slate-800/80 hover:bg-slate-700 border border-slate-700/70 text-slate-200 px-2 py-0.5 rounded transition text-[10px]"
          >
            Изменить директорию
          </button>
        </div>

        <!-- Лента профилей (без кнопки удаления) -->
        <div class="flex items-center gap-1 overflow-x-auto max-w-md">
          <div
            v-for="prof in store.profiles"
            :key="prof.id"
            @click="store.selectProfile(prof); store.addLog(`Сменен профиль: ${prof.name}`)"
            :class="store.currentProfile?.id === prof.id
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm font-semibold'
              : 'bg-slate-900/50 hover:bg-slate-800/60 text-slate-300 border-slate-700/60'"
            class="px-2 py-0.5 rounded border text-[11px] cursor-pointer flex items-center transition shrink-0"
          >
            <span>{{ prof.name }}</span>
          </div>
        </div>
      </div>

      <!-- Верхняя панель Строка 3: Статус выполнения слева | «Очистить» и «ВЫПОЛНИТЬ ЗАМЕНУ» справа -->
      <div class="px-3 py-1 border-b border-slate-800/60 bg-slate-950/35 flex flex-wrap items-center justify-between gap-2">
        <!-- Слева: статус применения -->
        <div class="text-[11px] font-bold tracking-wider uppercase">
          <span v-if="executionStatus === 'success'" class="text-emerald-400">
            УСПЕШНО ПРИМЕНЕНО
          </span>
          <span v-else-if="executionStatus === 'error'" class="text-rose-500">
            ОШИБКА ПРИМЕНЕНИЯ
          </span>
        </div>

        <!-- Справа: Очистить и ВЫПОЛНИТЬ ЗАМЕНУ -->
        <div class="flex items-center gap-2 ml-auto">
          <button
            @click="execHubRef?.clearField()"
            class="bg-slate-800/80 hover:bg-slate-700 text-slate-200 px-3 py-1 rounded transition border border-slate-700/70 text-[11px] font-medium"
          >
            Очистить
          </button>
          <button
            @click="execHubRef?.runExecution()"
            :disabled="!store.currentProject"
            class="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-bold px-4 py-1 rounded text-[11px] uppercase tracking-wider transition shadow-lg flex items-center gap-1.5"
          >
            ВЫПОЛНИТЬ ЗАМЕНУ
          </button>
        </div>
      </div>

      <!-- Центральная рабочая зона -->
      <ExecutionHub
        ref="execHubRef"
        :allow-management="allowManagement"
        @status-change="executionStatus = $event"
      />
    </div>

    <!-- СПЛИТТЕР РЕСАЙЗА СПРАВА -->
    <div @mousedown="startResizeRight" class="w-1 bg-slate-800/40 hover:bg-sky-500 cursor-col-resize transition shrink-0"></div>

    <!-- 3. ПРАВАЯ ПАНЕЛЬ -->
    <div :style="{ width: `${rightWidth}px` }" class="shrink-0">
      <HistoryPanel
        v-model:allowManagement="allowManagement"
        v-model:includeUnmarked="includeUnmarked"
        v-model:ignoreTests="ignoreTests"
        @open-file-modal="showFileModal = true"
        @open-view-modal="showViewModal = true"
      />
    </div>

    <!-- Модалка выбора файлов контекста -->
    <FileTreeModal v-if="showFileModal" @close="showFileModal = false" />

    <!-- Модалка просмотра прикрепленных файлов -->
    <AttachedFilesViewerModal v-if="showViewModal" @close="showViewModal = false" />

    <!-- Модалка создания проекта -->
    <div
      v-if="showNewProjectModal"
      @click.self="showNewProjectModal = false"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-lg shadow-2xl">
        <h3 class="text-base font-bold text-white mb-4">Добавить новый проект</h3>
        <div class="space-y-4">
          <div>
            <label class="text-xs text-slate-400 block mb-1">Название проекта</label>
            <input
              ref="newProjectNameInput"
              v-model="newProjName"
              type="text"
              placeholder="e.g. My Website"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
              @keydown.enter="handleCreateProject"
            />
          </div>
          <div>
            <label class="text-xs text-slate-400 block mb-1">Корневая папка проекта</label>
            <div class="flex gap-2">
              <input
                v-model="newProjDir"
                type="text"
                placeholder="Выберите через проводник или вставьте путь..."
                class="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
                @keydown.enter="handleCreateProject"
              />
              <button
                type="button"
                @click="handleBrowseFolderForNew"
                class="bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs px-3 py-1.5 rounded-lg transition shrink-0"
              >
                Обзор...
              </button>
            </div>
          </div>

          <div v-if="projectCreateError" class="p-2 bg-rose-950/60 border border-rose-800 text-rose-300 rounded text-xs">
            {{ projectCreateError }}
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-2">
          <button @click="showNewProjectModal = false" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
          <button @click="handleCreateProject" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition">
            Создать
          </button>
        </div>
      </div>
    </div>

    <!-- Модалка создания профиля -->
    <div
      v-if="showNewProfileModal"
      @click.self="showNewProfileModal = false"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h3 class="text-base font-bold text-white mb-3">Создать новый профиль</h3>
        <input
          ref="newProfileNameInput"
          v-model="newProfileName"
          type="text"
          placeholder="Например: Frontend-Focus"
          class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 mb-4"
          @keydown.enter="handleCreateProfile"
        />
        <div class="flex justify-end gap-2">
          <button @click="showNewProfileModal = false" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
          <button @click="handleCreateProfile" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition">
            Создать
          </button>
        </div>
      </div>
    </div>

    <!-- Модалки снапшотов -->
    <CreateSnapshotModal
      v-if="showCreateSnapshotModal"
      :active-profile-name="store.currentProfile?.name || 'default'"
      @close="showCreateSnapshotModal = false"
      @create="handleCreateSnapshot"
    />

    <SnapshotsListModal
      v-if="showSnapshotsListModal && store.currentProject"
      :project-id="store.currentProject.id"
      @close="showSnapshotsListModal = false"
      @restored="handleSnapshotRestored"
    />

    <SnapshotHelpModal
      v-if="showSnapshotHelpModal"
      @close="showSnapshotHelpModal = false"
    />

    <ConfigHelpModal
      v-if="showConfigHelpModal"
      @close="showConfigHelpModal = false"
    />

    <InstructionModal
      v-if="showInstructionModal"
      @close="showInstructionModal = false"
    />

    <!-- Модалка уведомления (сохранение/загрузка конфигурации и ошибки) -->
    <div
      v-if="notificationModal"
      @click.self="notificationModal = null"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-md shadow-2xl">
        <div class="flex items-center gap-2 mb-2.5">
          <span
            :class="notificationModal.type === 'success' ? 'text-emerald-400' : 'text-rose-400'"
            class="text-base font-bold"
          >
            {{ notificationModal.type === 'success' ? '✓' : '⚠' }}
          </span>
          <h3 class="text-sm font-bold text-white">{{ notificationModal.title }}</h3>
        </div>

        <p class="text-xs text-slate-300 leading-relaxed mb-3">
          {{ notificationModal.message }}
        </p>

        <div
          v-if="notificationModal.highlightPath"
          class="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-[11px] text-sky-300 break-all select-text mb-4"
        >
          {{ notificationModal.highlightPath }}
        </div>

        <div class="flex justify-end">
          <button
            @click="notificationModal = null"
            class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-5 py-1.5 rounded-lg transition shadow"
          >
            ОК
          </button>
        </div>
      </div>
    </div>

    <!-- Модалка списка профилей проекта для удаления -->
    <div
      v-if="showProfilesListModal"
      @click.self="showProfilesListModal = false"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-md shadow-2xl flex flex-col max-h-[75vh]">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-bold text-white">Управление профилями проекта</h3>
            <p class="text-[11px] text-slate-400 mt-0.5">
              Проект: <span class="text-sky-400 font-semibold">{{ store.currentProject?.name }}</span>
            </p>
          </div>
          <button
            @click="showProfilesListModal = false"
            class="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800"
          >
            Закрыть
          </button>
        </div>

        <div class="flex-1 overflow-y-auto space-y-1.5 pr-1">
          <div
            v-if="store.profiles.length === 0"
            class="text-xs text-slate-500 text-center py-6"
          >
            Профили не найдены
          </div>

          <div
            v-for="prof in store.profiles"
            :key="prof.id"
            class="flex items-center justify-between px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-xs font-medium text-slate-200 truncate">{{ prof.name }}</span>
              <span
                v-if="store.currentProfile?.id === prof.id"
                class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40"
              >
                Активный
              </span>
            </div>
            <button
              @click="askDeleteProfile(prof)"
              class="bg-rose-950/60 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-800/60 px-2.5 py-1 rounded text-[11px] font-medium transition shrink-0"
            >
              Удалить
            </button>
          </div>
        </div>

        <div class="mt-4 flex justify-end">
          <button
            @click="showProfilesListModal = false"
            class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-4 py-1.5 rounded-lg transition"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>

    <!-- Модалка подтверждения удаления профиля -->
    <div
      v-if="showDeleteProfileModal"
      @click.self="showDeleteProfileModal = false"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-sm shadow-2xl">
        <h3 class="text-sm font-bold text-white mb-2">Удаление профиля</h3>
        <p class="text-xs text-slate-300 mb-4">
          Вы действительно хотите удалить профиль <span class="text-amber-400 font-bold">"{{ profileToDelete?.name }}"</span>?
        </p>
        <div class="flex justify-end gap-2">
          <button @click="showDeleteProfileModal = false" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
          <button @click="confirmDeleteProfile" class="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition">
            Удалить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>