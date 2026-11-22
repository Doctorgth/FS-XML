<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useProjectStore } from '../../entities/projectStore';
import { api } from '../../shared/api/client';
import type { ChangeRecord } from '../../shared/api/types';
import FsignoreHelpModal from '../FsignoreHelpModal.vue';
import IgnoreEditorModal from '../IgnoreEditorModal.vue';

const props = defineProps<{
  allowManagement: boolean;
  includeUnmarked: boolean;
  ignoreTests?: boolean;
}>();

const emit = defineEmits([
  'update:allowManagement',
  'update:includeUnmarked',
  'update:ignoreTests',
  'openFileModal',
  'openViewModal',
]);

const store = useProjectStore();

// Редактор игноров
const showIgnoreModal = ref(false);
const ignoreModalTitle = ref('');
const ignoreModalContent = ref('');
const activeIgnoreType = ref<'global' | 'project'>('global');
const showFsignoreHelp = ref(false);

// Индикатор копирования ошибки
const copyToast = ref<string | null>(null);

// Модалка подтверждения отката при ручных правках
const showManualEditModal = ref(false);
const pendingRollbackRecord = ref<ChangeRecord | null>(null);

// Модалка подтверждения очистки истории
const showClearHistoryModal = ref(false);

// Анимация копирования промпта и модалка сохранения дампа
const promptCopied = ref(false);
let promptCopyTimer: ReturnType<typeof setTimeout> | null = null;
const dumpModal = ref<{ dumpPath: string } | null>(null);

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    showManualEditModal.value = false;
    showClearHistoryModal.value = false;
    dumpModal.value = null;
  }
}

onMounted(() => window.addEventListener('keydown', handleKeyDown));
onUnmounted(() => window.removeEventListener('keydown', handleKeyDown));

async function handleRollback(rec: ChangeRecord, force: boolean = false) {
  try {
    const res = await api.rollbackRecord(rec.id, force);
    if (!res.success && res.manual_edited) {
      pendingRollbackRecord.value = rec;
      showManualEditModal.value = true;
      return;
    }
    rec.status = 'rolled_back';
    showManualEditModal.value = false;
    pendingRollbackRecord.value = null;
    copyToast.value = `✓ Файл ${rec.target_path} успешно откатан!`;
    store.addLog(`Файл ${rec.target_path} откатан к оригинальному состоянию.`);
    if (store.currentProfile) {
      await store.selectProfile(store.currentProfile);
    }
    setTimeout(() => { copyToast.value = null; }, 3000);
  } catch (err: any) {
    copyToast.value = `⚠ Ошибка отката: ${err.message}`;
    store.addLog(`Ошибка отката: ${err.message}`);
    setTimeout(() => { copyToast.value = null; }, 4000);
  }
}

async function handleReapply(rec: ChangeRecord) {
  try {
    await api.reapplyRecord(rec.id);
    rec.status = 'success';
    copyToast.value = `✓ Повторно применено: ${rec.target_path}`;
    store.addLog(`Повторно применены правки ИИ для файла ${rec.target_path}`);
    if (store.currentProfile) {
      await store.selectProfile(store.currentProfile);
    }
    setTimeout(() => { copyToast.value = null; }, 3000);
  } catch (err: any) {
    copyToast.value = `⚠ Ошибка повторного применения: ${err.message}`;
    store.addLog(`Ошибка повторного применения: ${err.message}`);
    setTimeout(() => { copyToast.value = null; }, 4000);
  }
}

// Хранилище детальных записей сессий { [sessionId]: ChangeRecord[] }
const sessionDetails = ref<Record<number, ChangeRecord[]>>({});
const sessionDetailsErrors = ref<Record<number, string>>({});
const expandedSessions = ref<Set<number>>(new Set());

function formatLocalTime(utcStr: string): string {
  if (!utcStr) return '';
  const iso = utcStr.includes('T') ? utcStr : utcStr.replace(' ', 'T');
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) {
    return utcStr.replace('T', ' ').slice(0, 19);
  }
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

watch(
  () => store.currentProject?.id,
  () => {
    sessionDetails.value = {};
    sessionDetailsErrors.value = {};
    expandedSessions.value.clear();
  }
);

watch(
  () => store.history,
  async () => {
    for (const sid of expandedSessions.value) {
      try {
        sessionDetails.value[sid] = await api.getSessionDetails(sid);
      } catch {
        // ignore refresh errors
      }
    }
  }
);

async function toggleSessionDetails(sessionId: number) {
  if (expandedSessions.value.has(sessionId)) {
    expandedSessions.value.delete(sessionId);
    return;
  }

  expandedSessions.value.add(sessionId);
  if (!sessionDetails.value[sessionId]) {
    delete sessionDetailsErrors.value[sessionId];
    try {
      sessionDetails.value[sessionId] = await api.getSessionDetails(sessionId);
    } catch (err: any) {
      sessionDetailsErrors.value[sessionId] = err?.message || 'Ошибка загрузки деталей сессии';
    }
  }
}

async function retrySessionDetails(sessionId: number) {
  delete sessionDetailsErrors.value[sessionId];
  try {
    sessionDetails.value[sessionId] = await api.getSessionDetails(sessionId);
  } catch (err: any) {
    sessionDetailsErrors.value[sessionId] = err?.message || 'Ошибка загрузки деталей сессии';
  }
}

async function copyErrorContext(record: ChangeRecord) {
  if (record.status !== 'error') return;

  let message = 'Код не найден в файле';
  let searchBlock = '';
  let replaceBlock = '';
  let diskContent = '';

  if (record.error_details) {
    try {
      const parsed = JSON.parse(record.error_details);
      message = parsed.message || message;
      searchBlock = parsed.search_block || '';
      replaceBlock = parsed.replace_block || '';
      diskContent = parsed.actual_disk_content || '';
    } catch {
      message = record.error_details;
    }
  }

  const payload = [
    '=== СБОЙ ПРИМЕНЕНИЯ ПАТЧА ===',
    `Причина: ${message}`,
    `Целевой файл: ${record.target_path || 'Неизвестно'}`,
    '\n--- БЛОК ПОИСКА (<fs_search>) ---',
    searchBlock ? searchBlock : '(пусто)',
    '\n--- БЛОК ЗАМЕНЫ (<fs_replace>) ---',
    replaceBlock ? replaceBlock : '(пусто)',
    '\n--- АКТУАЛЬНОЕ СОДЕРЖИМОЕ ФАЙЛА НА ДИСКЕ ---',
    diskContent ? diskContent : (record.original_snapshot || '(файл пуст или не прочитан)'),
    '=== КОНЕЦ КОНТЕКСТА ОШИБКИ ==='
  ].join('\n');

  try {
    await navigator.clipboard.writeText(payload);
    copyToast.value = `✓ Скопирован контекст ошибки: ${record.target_path}`;
  } catch {
    copyToast.value = `⚠ Не удалось скопировать в буфер обмена`;
  }
  store.addLog(`Контекст ошибки скопирован для ${record.target_path}`);
  setTimeout(() => {
    copyToast.value = null;
  }, 3000);
}

async function openGlobalIgnore() {
  const res = await api.getGlobalIgnore();
  ignoreModalTitle.value = 'Глобальный игнор (fsignore_global)';
  ignoreModalContent.value = res.content;
  activeIgnoreType.value = 'global';
  showIgnoreModal.value = true;
}

async function openProjectIgnore() {
  if (!store.currentProject) return;
  const res = await api.getProjectIgnore(store.currentProject.id);
  ignoreModalTitle.value = `Проектный игнор (.fsignore) — ${store.currentProject.name}`;
  ignoreModalContent.value = res.content;
  activeIgnoreType.value = 'project';
  showIgnoreModal.value = true;
}

async function handleSaveIgnore(content: string) {
  if (activeIgnoreType.value === 'global') {
    await api.saveGlobalIgnore(content);
    store.addLog('Глобальный игнор сохранен.');
    if (store.currentProfile) {
      await store.selectProfile(store.currentProfile);
    }
  } else if (store.currentProject) {
    await api.saveProjectIgnore(store.currentProject.id, content);
    store.addLog('Проектный .fsignore сохранен.');
    if (store.currentProfile) {
      await store.selectProfile(store.currentProfile);
    }
  }
  showIgnoreModal.value = false;
}

function handleClearHistory() {
  if (!store.currentProject) return;
  showClearHistoryModal.value = true;
}

async function confirmClearHistory() {
  if (!store.currentProject) return;
  await api.clearHistory(store.currentProject.id);
  await store.loadHistory();
  sessionDetails.value = {};
  sessionDetailsErrors.value = {};
  expandedSessions.value.clear();
  store.addLog('История запусков проекта очищена.');
  showClearHistoryModal.value = false;
}

async function copyPrompt() {
  const res = await api.getSystemPrompt();
  try {
    await navigator.clipboard.writeText(res.prompt);
  } catch {
    // ignore clipboard errors in restricted environments
  }
  store.addLog('Системный промпт FS-XML скопирован.');
  promptCopied.value = true;
  if (promptCopyTimer) clearTimeout(promptCopyTimer);
  promptCopyTimer = setTimeout(() => {
    promptCopied.value = false;
  }, 2000);
}

async function copyDump() {
  if (!store.currentProject || !store.currentProfile) return;
  const res = await api.getDump(
    store.currentProject.id,
    store.currentProfile.id,
    props.includeUnmarked,
    props.ignoreTests ?? false
  );
  const savedPath = res.dump_path || `${store.currentProject.root_dir}/context_dump.txt`;
  store.addLog(`Дамп контекста сохранен: ${savedPath}`);
  dumpModal.value = { dumpPath: savedPath };
}
</script>

<template>
  <div class="h-full flex flex-col bg-slate-950/45 border-l border-slate-800/60 text-xs select-none relative">
    <!-- Всплывающий тост индикации копирования -->
    <div
      v-if="copyToast"
      class="absolute top-2 left-2 right-2 z-50 bg-sky-600 text-white text-[11px] font-bold px-3 py-2 rounded shadow-xl text-center border border-sky-400 transition-all duration-300"
    >
      {{ copyToast }}
    </div>

    <!-- Верхний блок: Прикрепленные файлы -->
    <div class="p-3 border-b border-slate-800/60">
      <div class="text-[11px] font-bold text-slate-200 uppercase tracking-wider mb-2">
        Прикрепленные файлы ({{ store.files.filter(f => f.state !== 'unmarked').length }})
      </div>
      <div class="flex gap-2">
        <button
          :disabled="!store.currentProject"
          @click="emit('openFileModal')"
          class="flex-1 bg-slate-800/80 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-medium py-1.5 px-2 rounded border border-slate-700/70 transition"
        >
          Редактировать
        </button>
        <button
          :disabled="!store.currentProject"
          @click="emit('openViewModal')"
          class="flex-1 bg-slate-800/80 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-medium py-1.5 px-2 rounded border border-slate-700/70 transition"
        >
          Просмотр
        </button>
      </div>
    </div>

    <!-- Заголовок истории с подсказкой (i) -->
    <div class="px-3 py-2 border-b border-slate-800/60 flex justify-between items-center">
      <div class="flex items-center gap-1.5">
        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">История запусков (Откат)</span>
        <span
          class="text-slate-500 hover:text-sky-400 cursor-help font-bold text-xs"
          title="Каждая сессия фиксирует выполненные замены. При клике на ошибку в буфер сразу копируется сбойный кусок и актуальный файл на диске."
        >
          ⓘ
        </span>
      </div>
    </div>

    <!-- Список истории запусков с деталями сессий -->
    <div class="flex-1 overflow-y-auto p-2.5 space-y-2">
      <div v-if="store.history.length === 0" class="text-xs text-slate-500 text-center py-6">
        История запусков пуста
      </div>

      <div
        v-for="item in store.history"
        :key="item.id"
        class="bg-slate-950/35 border border-slate-700/60 rounded overflow-hidden"
      >
        <!-- Шапка блока сессии -->
        <div
          @click="toggleSessionDetails(item.id)"
          class="p-2 cursor-pointer hover:bg-slate-850 flex justify-between items-center transition"
        >
          <div class="flex items-center gap-1.5 truncate mr-2">
            <span class="text-slate-500 font-mono text-[10px]">{{ expandedSessions.has(item.id) ? '▼' : '▶' }}</span>
            <span class="text-[10px] text-slate-300 font-mono truncate">Сессия: {{ formatLocalTime(item.created_at) }}</span>
          </div>
          <span
            :class="item.status === 'success' ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60' : 'text-rose-400 bg-rose-950/60 border-rose-800/60'"
            class="font-bold text-[10px] uppercase px-1.5 py-0.5 rounded border"
          >
            {{ item.status === 'success' ? 'Success' : `Errors: ${item.error_count}` }}
          </span>
        </div>

        <!-- Развернутый список файлов сессии -->
        <div v-if="expandedSessions.has(item.id)" class="border-t border-slate-800/60 p-1.5 space-y-1 bg-slate-950/30">
          <div v-if="sessionDetailsErrors[item.id]" class="text-[10px] text-rose-400 py-1.5 px-2 text-center space-y-1">
            <div>⚠ {{ sessionDetailsErrors[item.id] }}</div>
            <button
              @click.stop="retrySessionDetails(item.id)"
              class="text-sky-400 hover:text-sky-300 underline"
            >
              Повторить
            </button>
          </div>
          <div v-else-if="!sessionDetails[item.id]" class="text-[10px] text-slate-500 py-1 text-center">
            Загрузка файлов...
          </div>

          <div
            v-for="rec in sessionDetails[item.id] || []"
            :key="rec.id"
            @click="rec.status === 'error' ? copyErrorContext(rec) : null"
            :class="[
              rec.status === 'success'
                ? 'bg-slate-900/60 border-slate-800 text-slate-300'
                : (rec.status === 'rolled_back'
                    ? 'bg-slate-900/30 border-slate-800/60 text-slate-500'
                    : 'bg-rose-950/40 border-rose-900/60 text-rose-300 hover:bg-rose-900/50 cursor-pointer shadow-sm')
            ]"
            class="px-2 py-1 border rounded text-[11px] font-mono flex items-center justify-between transition"
            :title="rec.status === 'error' ? 'Нажмите, чтобы скопировать ошибку и актуальный файл в буфер!' : ''"
          >
            <div class="truncate mr-2 flex items-center gap-1.5">
              <span>📄</span>
              <span class="truncate">{{ rec.target_path || rec.command_tag }}</span>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <span
                :class="[
                  rec.status === 'success' ? 'text-emerald-400 font-semibold' : '',
                  rec.status === 'error' ? 'text-rose-400 font-bold' : '',
                  rec.status === 'rolled_back' ? 'text-slate-500 line-through' : ''
                ]"
                class="text-[10px]"
              >
                [{{ rec.status === 'success' ? 'Success' : (rec.status === 'rolled_back' ? 'RolledBack' : 'Failed') }}]
              </span>

              <button
                v-if="rec.status === 'success' && (rec.command_tag === 'fs_create' || rec.command_tag === 'fs_edit')"
                @click.stop="handleRollback(rec, false)"
                class="bg-slate-800 hover:bg-amber-600 text-slate-300 hover:text-white px-1.5 py-0.5 rounded text-[10px] border border-slate-700 transition"
                title="Откатить изменения этого файла"
              >
                Откатить
              </button>

              <button
                v-if="rec.status === 'rolled_back' && (rec.command_tag === 'fs_create' || rec.command_tag === 'fs_edit')"
                @click.stop="handleReapply(rec)"
                class="bg-slate-800 hover:bg-emerald-600 text-emerald-300 hover:text-white px-1.5 py-0.5 rounded text-[10px] border border-emerald-800/60 transition"
                title="Повторно применить правку нейросети (откатить откат)"
              >
                Повторить
              </button>

              <span v-if="rec.status === 'error'" class="text-[10px] text-sky-400 underline">Скопировать</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Нижняя панель действий -->
    <div class="p-3 border-t border-slate-800/60 flex flex-col gap-2.5">
      <!-- Чекбоксы с подсказками (i) -->
      <div class="space-y-2 text-[11px] text-slate-300">
        <div class="flex items-center justify-between">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              :checked="allowManagement"
              @change="emit('update:allowManagement', ($event.target as HTMLInputElement).checked)"
              class="accent-sky-500 rounded"
            />
            <span :class="allowManagement ? 'text-amber-400 font-semibold' : 'text-slate-400'">Управляющие команды</span>
          </label>
          <span
            class="text-slate-500 hover:text-sky-400 cursor-help font-bold text-xs px-1"
            title="Разрешает нейросети создавать профили и менять статус прав файлов через XML."
          >
            ⓘ
          </span>
        </div>

        <div class="flex items-center justify-between">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              :checked="includeUnmarked"
              @change="emit('update:includeUnmarked', ($event.target as HTMLInputElement).checked)"
              class="accent-sky-500 rounded"
            />
            <span class="text-slate-400">Имена неотмеченных файлов</span>
          </label>
          <span
            class="text-slate-500 hover:text-sky-400 cursor-help font-bold text-xs px-1"
            title="Добавляет в дамп контекста список путей неотмеченных файлов проекта без содержимого."
          >
            ⓘ
          </span>
        </div>

        <div class="flex items-center justify-between">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              :checked="ignoreTests"
              @change="emit('update:ignoreTests', ($event.target as HTMLInputElement).checked)"
              class="accent-sky-500 rounded"
            />
            <span class="text-slate-400">Игнорировать тесты</span>
          </label>
          <span
            class="text-slate-500 hover:text-sky-400 cursor-help font-bold text-xs px-1"
            title="Не добавляет в дамп файлы с test_ или _test в названии. Отмеченные тестовые файлы помечаются как существующие без содержимого."
          >
            ⓘ
          </span>
        </div>
      </div>

      <!-- Кнопки fsignore -->
      <div class="flex gap-2">
        <button
          :disabled="!store.currentProject"
          @click="openProjectIgnore"
          class="flex-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 border border-slate-700 py-1.5 rounded transition text-[11px]"
          title="Локальный .fsignore для текущего проекта"
        >
          📁 Проектный fsignore
        </button>
        <button
          @click="openGlobalIgnore"
          class="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 py-1.5 rounded transition text-[11px]"
          title="Глобальный fsignore для всех проектов программы"
        >
          🌐 Глобальный fsignore
        </button>
      </div>

      <!-- Плашка справки fsignore -->
      <button
        @click="showFsignoreHelp = true"
        class="w-full bg-slate-900/40 hover:bg-slate-800/60 border border-dashed border-slate-700/70 hover:border-sky-500/60 py-1 px-2 rounded text-[11px] text-slate-300 hover:text-sky-300 transition flex items-center justify-center gap-1.5"
      >
        <span>💡</span>
        <span>Как работает и на что влияет fsignore?</span>
      </button>

      <!-- Кнопка промпта -->
      <button
        @click="copyPrompt"
        :class="promptCopied
          ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300 scale-[1.02]'
          : 'bg-slate-800/80 hover:bg-slate-700/90 text-slate-200 border-slate-700'"
        class="w-full border py-1.5 rounded transition-all duration-200 text-center font-medium flex items-center justify-center gap-1.5"
      >
        <span v-if="promptCopied" class="inline-block animate-bounce">✓</span>
        <span>{{ promptCopied ? 'СКОПИРОВАНО В БУФЕР!' : 'КОПИРОВАТЬ ПРОМПТ' }}</span>
      </button>

      <!-- Создать дамп -->
      <button
        :disabled="!store.currentProject"
        @click="copyDump"
        class="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white font-bold py-2 rounded transition text-center shadow"
      >
        СОЗДАТЬ ДАМП КОНТЕКСТА
      </button>

      <!-- Очистить сессии -->
      <button
        :disabled="!store.currentProject || store.history.length === 0"
        @click="handleClearHistory"
        class="w-full bg-rose-950/40 hover:bg-rose-900/60 disabled:opacity-30 text-rose-300 border border-rose-900/60 py-1.5 rounded transition text-center"
      >
        Очистить историю сессий
      </button>
    </div>

    <!-- Модалки -->
    <IgnoreEditorModal
      v-if="showIgnoreModal"
      :title="ignoreModalTitle"
      :initial-content="ignoreModalContent"
      @close="showIgnoreModal = false"
      @save="handleSaveIgnore"
    />

    <FsignoreHelpModal
      v-if="showFsignoreHelp"
      @close="showFsignoreHelp = false"
    />

    <!-- Модалка уведомления о сохранении дампа контекста -->
    <div
      v-if="dumpModal"
      @click.self="dumpModal = null"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-md shadow-2xl">
        <div class="flex items-center gap-2 mb-2.5">
          <span class="text-emerald-400 text-base font-bold">✓</span>
          <h3 class="text-sm font-bold text-white">Дамп контекста сохранен</h3>
        </div>
        <p class="text-xs text-slate-300 leading-relaxed mb-3">
          Дамп контекста сохранен в корень проекта в файл
          <span class="font-mono text-amber-300 font-semibold">context_dump.txt</span>:
        </p>
        <div class="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-[11px] text-sky-300 break-all select-text mb-4">
          {{ dumpModal.dumpPath }}
        </div>
        <div class="flex justify-end">
          <button
            @click="dumpModal = null"
            class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-5 py-1.5 rounded-lg transition shadow"
          >
            ОК
          </button>
        </div>
      </div>
    </div>

    <!-- Модалка предупреждения о ручных правках перед откатом -->
    <div
      v-if="showManualEditModal"
      @click.self="showManualEditModal = false"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-sm shadow-2xl">
        <h3 class="text-sm font-bold text-amber-400 mb-2">⚠ Файл изменен вручную!</h3>
        <p class="text-xs text-slate-300 mb-4">
          Файл <span class="font-mono text-white font-bold">{{ pendingRollbackRecord?.target_path }}</span> был отредактирован после того, как к нему применили ИИ-правки.<br/><br/>
          Вы уверены, что хотите затереть ручные правки и вернуть файл к оригинальному снимку?
        </p>
        <div class="flex justify-end gap-2">
          <button @click="showManualEditModal = false" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
          <button
            @click="pendingRollbackRecord && handleRollback(pendingRollbackRecord, true)"
            class="bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs px-4 py-1.5 rounded transition shadow"
          >
            Да, перезаписать
          </button>
        </div>
      </div>
    </div>

    <!-- Модалка подтверждения очистки истории запусков -->
    <div
      v-if="showClearHistoryModal"
      @click.self="showClearHistoryModal = false"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
    >
      <div class="bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-sm shadow-2xl">
        <h3 class="text-sm font-bold text-white mb-2">Очистка истории запусков</h3>
        <p class="text-xs text-slate-300 mb-4 leading-relaxed">
          Вы уверены, что хотите полностью очистить историю запусков проекта
          <span class="text-amber-400 font-bold">"{{ store.currentProject?.name }}"</span>?
          <br /><br />
          Все записи сессий и возможность отката прошлых правок будут удалены.
        </p>
        <div class="flex justify-end gap-2">
          <button @click="showClearHistoryModal = false" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
          <button
            @click="confirmClearHistory"
            class="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition shadow"
          >
            Очистить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>