<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { api } from '../shared/api/client';

const props = defineProps<{
  projectId: number;
}>();

const emit = defineEmits(['close', 'restored']);

const snapshots = ref<Array<{ id: number; profile_id: number | null; name: string; created_at: string; profile_name: string | null }>>([]);

function formatLocalTime(utcStr: string): string {
  if (!utcStr) return '';
  const iso = utcStr.includes('T') ? utcStr : utcStr.replace(' ', 'T');
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) {
    return utcStr.replace('T', ' ').slice(0, 16);
  }
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
const loading = ref(false);
const errorMsg = ref('');
const pendingAction = ref<{ type: 'restore' | 'delete'; snap: { id: number; name: string } } | null>(null);

async function loadList() {
  loading.value = true;
  errorMsg.value = '';
  try {
    snapshots.value = await api.getSnapshots(props.projectId);
  } catch (err: any) {
    errorMsg.value = err.message || 'Не удалось загрузить список снапшотов.';
  } finally {
    loading.value = false;
  }
}

function askRestore(snap: { id: number; name: string }) {
  errorMsg.value = '';
  pendingAction.value = { type: 'restore', snap };
}

function askDelete(snap: { id: number; name: string }) {
  errorMsg.value = '';
  pendingAction.value = { type: 'delete', snap };
}

async function confirmPendingAction() {
  if (!pendingAction.value) return;
  const { type, snap } = pendingAction.value;
  errorMsg.value = '';
  try {
    if (type === 'restore') {
      await api.restoreSnapshot(snap.id);
      pendingAction.value = null;
      emit('restored');
      emit('close');
    } else {
      await api.deleteSnapshot(snap.id);
      pendingAction.value = null;
      await loadList();
    }
  } catch (err: any) {
    errorMsg.value = err.message || 'Ошибка выполнения операции со снапшотом.';
    pendingAction.value = null;
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (pendingAction.value) {
      pendingAction.value = null;
      return;
    }
    emit('close');
  }
}

onMounted(() => {
  loadList();
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => window.removeEventListener('keydown', handleKeyDown));
</script>

<template>
  <div
    @click.self="emit('close')"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
  >
    <div class="bg-slate-900 border border-slate-700 w-full max-w-2xl h-[70vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
      <div class="px-5 py-3.5 border-b border-slate-800 flex justify-between items-center bg-slate-950">
        <h3 class="text-sm font-bold text-white tracking-wide">📂 Сохраненные снапшоты проекта</h3>
        <button @click="emit('close')" class="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800">
          Закрыть (Esc)
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-2">
        <div v-if="errorMsg" class="p-2.5 bg-rose-950/60 border border-rose-800 rounded text-xs text-rose-300">
          {{ errorMsg }}
        </div>
        <div v-if="loading" class="text-xs text-slate-500 text-center py-8">Загрузка...</div>
        <div v-else-if="snapshots.length === 0" class="text-xs text-slate-500 text-center py-8">Снапшотов пока нет. Создайте первый!</div>

        <div
          v-for="snap in snapshots"
          :key="snap.id"
          class="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between hover:border-slate-700 transition"
        >
          <div>
            <div class="text-xs font-bold text-white">{{ snap.name }}</div>
            <div class="text-[11px] text-slate-400 font-mono mt-0.5">
              <span>{{ formatLocalTime(snap.created_at) }}</span>
              <span class="mx-1.5">|</span>
              <span class="text-amber-400">{{ snap.profile_name ? `Профиль: ${snap.profile_name}` : (snap.profile_id !== null ? 'Удалённый профиль' : 'Все профили') }}</span>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              @click="askRestore(snap)"
              class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-3 py-1.5 rounded transition shadow"
            >
              Загрузить
            </button>
            <button
              @click="askDelete(snap)"
              class="text-rose-400 hover:text-rose-300 bg-rose-950/40 border border-rose-900/60 px-2.5 py-1.5 rounded text-xs transition"
              title="Удалить снапшот"
            >
              Удалить
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="pendingAction"
        class="px-5 py-3 border-t border-slate-800 bg-slate-900 flex items-center justify-between gap-3"
      >
        <span class="text-xs text-slate-200">
          <template v-if="pendingAction.type === 'restore'">
            Восстановить проект к снапшоту <strong class="text-amber-300">"{{ pendingAction.snap.name }}"</strong>? Текущие файлы будут перезаписаны.
          </template>
          <template v-else>
            Удалить снапшот <strong class="text-rose-300">"{{ pendingAction.snap.name }}"</strong>?
          </template>
        </span>
        <div class="flex items-center gap-2 shrink-0">
          <button @click="pendingAction = null" class="px-3 py-1 text-xs text-slate-400 hover:text-white">Отмена</button>
          <button
            @click="confirmPendingAction"
            :class="pendingAction.type === 'restore' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'"
            class="text-white text-xs font-semibold px-3 py-1 rounded transition"
          >
            {{ pendingAction.type === 'restore' ? 'Восстановить' : 'Удалить' }}
          </button>
        </div>
      </div>

      <div class="px-5 py-3 border-t border-slate-800 bg-slate-950 flex justify-end">
        <button @click="emit('close')" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-4 py-1.5 rounded">
          Закрыть
        </button>
      </div>
    </div>
  </div>
</template>