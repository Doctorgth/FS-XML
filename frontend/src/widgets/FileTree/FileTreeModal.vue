<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useProjectStore } from '../../entities/projectStore';
import type { FileState } from '../../shared/api/types';

const emit = defineEmits(['close']);
const store = useProjectStore();

const searchInput = ref('');
const appliedSearchQuery = ref('');
const searchTarget = ref<'all' | 'files' | 'dirs'>('all');
const collapsedDirs = ref<Set<string>>(new Set());

function applySearch() {
  appliedSearchQuery.value = searchInput.value;
}

interface TreeItem {
  path: string;
  name: string;
  isDir: boolean;
  depth: number;
  state: FileState;
}

const allDirs = computed(() => {
  const dirs = new Set<string>();
  for (const f of store.files) {
    const parts = f.path.split('/');
    for (let i = 1; i < parts.length; i++) {
      dirs.add(parts.slice(0, i).join('/'));
    }
  }
  return Array.from(dirs).sort();
});

onMounted(() => {
  collapsedDirs.value = new Set(allDirs.value);
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close');
}

const treeItems = computed<TreeItem[]>(() => {
  const allNodes: TreeItem[] = [];

  for (const dir of allDirs.value) {
    const parts = dir.split('/');
    allNodes.push({
      path: dir,
      name: parts[parts.length - 1],
      isDir: true,
      depth: parts.length - 1,
      state: 'unmarked',
    });
  }

  for (const f of store.files) {
    const parts = f.path.split('/');
    allNodes.push({
      path: f.path,
      name: f.name,
      isDir: false,
      depth: parts.length - 1,
      state: f.state,
    });
  }

  allNodes.sort((a, b) => a.path.localeCompare(b.path));
  return allNodes;
});

function isHiddenByCollapsedParent(itemPath: string): boolean {
  const parts = itemPath.split('/');
  for (let i = 1; i < parts.length; i++) {
    const parentDir = parts.slice(0, i).join('/');
    if (collapsedDirs.value.has(parentDir)) {
      return true;
    }
  }
  return false;
}

const filteredItems = computed(() => {
  const q = appliedSearchQuery.value.trim();

  return treeItems.value.filter((item) => {
    if (!q && isHiddenByCollapsedParent(item.path)) {
      return false;
    }

    if (searchTarget.value === 'files' && item.isDir) return false;
    if (searchTarget.value === 'dirs' && !item.isDir) return false;

    if (!q) return true;

    // Автоматическое определение режима: если есть regex спецсимволы/маски
    if (q.includes('*') || q.includes('?')) {
      try {
        const escaped = q
          .replace(/[.+^${}()|[\]\\]/g, '\\$&')
          .replace(/\*/g, '.*')
          .replace(/\?/g, '.');
        const re = new RegExp('^' + escaped + '$', 'i');
        return re.test(item.name) || re.test(item.path);
      } catch {
        return item.path.toLowerCase().includes(q.toLowerCase());
      }
    }

    if (q.startsWith('^') || q.endsWith('$')) {
      try {
        const re = new RegExp(q, 'i');
        return re.test(item.path);
      } catch {
        // fallback to includes
      }
    }

    return item.path.toLowerCase().includes(q.toLowerCase());
  });
});

function toggleCollapse(dirPath: string) {
  if (collapsedDirs.value.has(dirPath)) {
    collapsedDirs.value.delete(dirPath);
  } else {
    collapsedDirs.value.add(dirPath);
  }
}

function expandAll() {
  collapsedDirs.value.clear();
}

function collapseAll() {
  collapsedDirs.value = new Set(allDirs.value);
}

const dirStatesMap = computed<Record<string, FileState | 'mixed'>>(() => {
  const acc: Record<string, { first: FileState; allSame: boolean }> = {};
  for (const f of store.files) {
    const parts = f.path.split('/');
    for (let i = 1; i < parts.length; i++) {
      const dir = parts.slice(0, i).join('/');
      const entry = acc[dir];
      if (!entry) {
        acc[dir] = { first: f.state, allSame: true };
      } else if (entry.allSame && entry.first !== f.state) {
        entry.allSame = false;
      }
    }
  }
  const res: Record<string, FileState | 'mixed'> = {};
  for (const [dir, info] of Object.entries(acc)) {
    res[dir] = info.allSame ? info.first : 'mixed';
  }
  return res;
});

function getDirState(dirPath: string): FileState | 'mixed' {
  return dirStatesMap.value[dirPath] || 'unmarked';
}

async function toggleNodeState(item: TreeItem, targetState: FileState) {
  if (!item.isDir) {
    const next = item.state === targetState ? 'unmarked' : targetState;
    await store.updateFileState(item.path, next);
  } else {
    const prefix = item.path + '/';
    const children = store.files.filter((f) => f.path.startsWith(prefix));
    const currentDirState = getDirState(item.path);
    const next = currentDirState === targetState ? 'unmarked' : targetState;
    await store.updateFilesStateBulk(
      children.map((c) => c.path),
      next
    );
  }
}

async function markAllFiltered(targetState: FileState) {
  const filePaths = filteredItems.value.filter((item) => !item.isDir).map((item) => item.path);
  await store.updateFilesStateBulk(filePaths, targetState);
}

// Статистика отмеченных файлов
const writableCount = computed(() => store.files.filter((f) => f.state === 'writable').length);
const readonlyCount = computed(() => store.files.filter((f) => f.state === 'readonly').length);
</script>

<template>
  <div
    @click.self="emit('close')"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
  >
    <div class="bg-slate-900 border border-slate-700 w-full max-w-4xl h-[85vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
      <!-- Шапка модалки -->
      <div class="px-6 py-3.5 border-b border-slate-800 flex justify-between items-center bg-slate-950">
        <div>
          <h2 class="text-base font-bold text-slate-100">Выбор файлов контекста</h2>
          <p class="text-xs text-slate-400 mt-0.5">Текущий профиль: <span class="text-amber-400 font-medium">{{ store.currentProfile?.name }}</span></p>
        </div>
        <button @click="emit('close')" class="text-slate-400 hover:text-white px-3 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 transition">
          Закрыть (Esc)
        </button>
      </div>

      <!-- Поисковая панель -->
      <div class="p-3 bg-slate-800/50 border-b border-slate-700/60 flex flex-wrap gap-2.5 items-center justify-between">
        <div class="flex gap-2 items-center flex-1 min-w-[280px]">
          <div class="relative flex-1 flex items-center">
            <input
              v-model="searchInput"
              @keydown.enter="applySearch"
              type="text"
              placeholder="Поиск (*.ts, app.py, ^src/)..."
              class="bg-slate-950 border border-slate-700 rounded-lg pl-3 pr-14 py-1.5 text-xs w-full text-slate-200 focus:outline-none focus:border-sky-500"
            />
            <span class="absolute right-2.5 text-[10px] text-slate-500 pointer-events-none select-none font-mono">
              Enter ↵
            </span>
          </div>
          <button
            @click="applySearch"
            class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition shrink-0"
          >
            Поиск
          </button>
          <select v-model="searchTarget" class="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none">
            <option value="all">Все</option>
            <option value="files">Только файлы</option>
            <option value="dirs">Только папки</option>
          </select>
        </div>

        <div class="flex gap-1.5">
          <button @click="expandAll" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded border border-slate-700">
            Развернуть
          </button>
          <button @click="collapseAll" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded border border-slate-700">
            Свернуть
          </button>
          <button @click="markAllFiltered('writable')" class="bg-sky-600/30 text-sky-400 border border-sky-500/40 hover:bg-sky-600/50 px-2 py-1 text-xs rounded font-medium">
            В Writable
          </button>
          <button @click="markAllFiltered('readonly')" class="bg-amber-600/30 text-amber-400 border border-amber-500/40 hover:bg-amber-600/50 px-2 py-1 text-xs rounded font-medium">
            В Read-Only
          </button>
          <button @click="markAllFiltered('unmarked')" class="bg-slate-700 hover:bg-slate-600 text-slate-300 px-2 py-1 text-xs rounded">
            Сбросить
          </button>
        </div>
      </div>

      <!-- Дерево файлов -->
      <div class="flex-1 overflow-y-auto p-3 space-y-0.5 font-mono text-xs">
        <div
          v-for="item in filteredItems"
          :key="item.path"
          :style="{ paddingLeft: `${item.depth * 18 + 8}px` }"
          class="flex items-center justify-between py-1 px-2 rounded hover:bg-slate-800/70 transition"
        >
          <div class="flex items-center gap-2 truncate mr-4">
            <!-- Стрелка папки -->
            <span
              v-if="item.isDir"
              @click="toggleCollapse(item.path)"
              class="cursor-pointer text-amber-400 font-bold text-xs w-4 inline-block text-center"
            >
              {{ collapsedDirs.has(item.path) ? '▶' : '▼' }}
            </span>
            <span v-else class="w-4 inline-block"></span>

            <!-- Иконка 📁 или 📄 -->
            <span class="text-sm select-none">{{ item.isDir ? '📁' : '📄' }}</span>

            <!-- Имя -->
            <span
              @click="item.isDir ? toggleCollapse(item.path) : null"
              :class="[
                item.isDir ? 'text-amber-300 font-semibold cursor-pointer' : 'text-slate-300',
                item.state === 'writable' ? 'text-sky-400 font-bold' : '',
                item.state === 'readonly' ? 'text-amber-400 font-bold' : ''
              ]"
              class="truncate"
            >
              {{ item.name }}
            </span>
          </div>

          <div class="flex gap-1.5 items-center shrink-0">
            <button
              @click="toggleNodeState(item, 'writable')"
              :class="(item.isDir ? getDirState(item.path) === 'writable' : item.state === 'writable') ? 'bg-sky-500 text-white font-bold' : 'bg-slate-800 text-slate-400 border border-slate-700'"
              class="w-7 h-6 text-[11px] rounded flex items-center justify-center transition"
              title="Разрешить запись (Writable)"
            >
              W
            </button>

            <button
              @click="toggleNodeState(item, 'readonly')"
              :class="(item.isDir ? getDirState(item.path) === 'readonly' : item.state === 'readonly') ? 'bg-amber-500 text-slate-950 font-bold' : 'bg-slate-800 text-slate-400 border border-slate-700'"
              class="w-7 h-6 text-[11px] rounded flex items-center justify-center transition"
              title="Только чтение (Read-Only)"
            >
              RO
            </button>
          </div>
        </div>
      </div>

      <!-- Футер со счетчиками Writable и Read-Only -->
      <div class="px-6 py-3 border-t border-slate-800 bg-slate-950 flex justify-between items-center text-xs">
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-sky-500 inline-block"></span>
            <span class="text-slate-400">Writable:</span>
            <span class="text-sky-400 font-bold font-mono">{{ writableCount }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span>
            <span class="text-slate-400">Read-Only:</span>
            <span class="text-amber-400 font-bold font-mono">{{ readonlyCount }}</span>
          </div>
        </div>

        <button @click="emit('close')" class="bg-sky-600 hover:bg-sky-500 text-white font-medium px-5 py-1.5 rounded-lg transition shadow">
          Готово
        </button>
      </div>
    </div>
  </div>
</template>