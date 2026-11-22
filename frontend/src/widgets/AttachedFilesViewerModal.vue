<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useProjectStore } from '../entities/projectStore';
import { api } from '../shared/api/client';
import type { FileTreeNode } from '../shared/api/types';

const emit = defineEmits(['close']);
const store = useProjectStore();

const attachedFiles = computed(() =>
  store.files.filter((f) => f.state === 'writable' || f.state === 'readonly')
);

const searchQuery = ref('');

const filteredFiles = computed(() => {
  const q = searchQuery.value.trim();
  if (!q) return attachedFiles.value;

  if (q.includes('*') || q.includes('?')) {
    try {
      const escaped = q
        .replace(/[.+^${}()|[\]\\]/g, '\\$&')
        .replace(/\*/g, '.*')
        .replace(/\?/g, '.');
      const re = new RegExp('^' + escaped + '$', 'i');
      return attachedFiles.value.filter((f) => re.test(f.name) || re.test(f.path));
    } catch {
      // fallback
    }
  }

  if (q.startsWith('^') || q.endsWith('$')) {
    try {
      const re = new RegExp(q, 'i');
      return attachedFiles.value.filter((f) => re.test(f.path));
    } catch {
      // fallback
    }
  }

  if (q.startsWith('/') && q.lastIndexOf('/') > 0) {
    try {
      const lastSlash = q.lastIndexOf('/');
      const pattern = q.slice(1, lastSlash);
      const flags = q.slice(lastSlash + 1) || 'i';
      const re = new RegExp(pattern, flags);
      return attachedFiles.value.filter((f) => re.test(f.path));
    } catch {
      // fallback
    }
  }

  return attachedFiles.value.filter((f) => f.path.toLowerCase().includes(q.toLowerCase()));
});

const selectedFile = ref<FileTreeNode | null>(null);
const fileContent = ref('');
const loading = ref(false);
const copied = ref(false);
let activeRequestId = 0;

async function selectFile(file: FileTreeNode) {
  if (!store.currentProject) return;
  const reqId = ++activeRequestId;
  selectedFile.value = file;
  loading.value = true;
  fileContent.value = '';
  try {
    const res = await api.getFileContent(store.currentProject.id, file.path);
    if (reqId !== activeRequestId) return;
    fileContent.value = res.content;
  } catch (err: any) {
    if (reqId !== activeRequestId) return;
    fileContent.value = `Ошибка загрузки файла: ${err.message}`;
  } finally {
    if (reqId === activeRequestId) {
      loading.value = false;
    }
  }
}

async function copyCurrentCode() {
  if (!fileContent.value) return;
  try {
    await navigator.clipboard.writeText(fileContent.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  } catch {
    // ignore clipboard errors in restricted environments
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close');
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
  if (attachedFiles.value.length > 0) {
    selectFile(attachedFiles.value[0]);
  }
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <div
    @click.self="emit('close')"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
  >
    <div class="bg-slate-900 border border-slate-700 w-full max-w-5xl h-[85vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
      <!-- Заголовок -->
      <div class="px-5 py-3.5 border-b border-slate-800 flex justify-between items-center bg-slate-950">
        <div>
          <h3 class="text-sm font-bold text-white tracking-wide">👁 Просмотр прикрепленных файлов ({{ attachedFiles.length }})</h3>
          <p class="text-[11px] text-slate-400">Профиль: <span class="text-amber-400 font-medium">{{ store.currentProfile?.name }}</span></p>
        </div>
        <button @click="emit('close')" class="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800">
          Закрыть (Esc)
        </button>
      </div>

      <!-- Двухоконное содержимое -->
      <div class="flex-1 flex min-h-0">
        <!-- Левый список файлов -->
        <div class="w-72 border-r border-slate-800 bg-slate-950 flex flex-col min-h-0">
          <div class="p-2 border-b border-slate-800 bg-slate-900/40">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Поиск (*.ts, app.py, ^src/)..."
              class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div class="flex-1 overflow-y-auto p-2 space-y-1">
            <div v-if="attachedFiles.length === 0" class="text-xs text-slate-500 text-center py-8">
              Нет прикрепленных файлов.<br/>Нажмите "Редактировать", чтобы выбрать файлы.
            </div>
            <div v-else-if="filteredFiles.length === 0" class="text-xs text-slate-500 text-center py-8">
              Ничего не найдено по запросу
            </div>

            <div
              v-for="file in filteredFiles"
              :key="file.path"
              @click="selectFile(file)"
              :class="selectedFile?.path === file.path ? 'bg-sky-950/60 border-sky-700 text-white' : 'border-transparent text-slate-400 hover:bg-slate-900'"
              class="px-2.5 py-1.5 border rounded cursor-pointer flex items-center justify-between text-xs font-mono transition"
            >
              <span class="truncate mr-2">📄 {{ file.path }}</span>
              <span
                :class="file.state === 'writable' ? 'text-sky-400 bg-sky-950/60' : 'text-amber-400 bg-amber-950/60'"
                class="text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0"
              >
                {{ file.state === 'writable' ? 'W' : 'RO' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Правый просмотрщик кода -->
        <div class="flex-1 flex flex-col bg-slate-950 min-w-0">
          <div v-if="selectedFile" class="px-4 py-2 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center text-xs">
            <span class="font-mono text-slate-200 font-semibold truncate">{{ selectedFile.path }}</span>
            <button
              @click="copyCurrentCode"
              class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1 rounded border border-slate-700 text-[11px] transition"
            >
              {{ copied ? '✓ Скопировано' : 'Копировать код' }}
            </button>
          </div>

          <div class="flex-1 overflow-auto p-4 select-text">
            <div v-if="!selectedFile" class="text-xs text-slate-500 text-center py-12">Выберите файл слева для чтения содержимого</div>
            <div v-else-if="loading" class="text-xs text-slate-500">Загрузка содержимого...</div>
            <pre v-else class="font-mono text-xs text-slate-200 whitespace-pre-wrap break-words leading-relaxed">{{ fileContent }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>