<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue';

defineProps<{
  activeProfileName: string;
}>();

const emit = defineEmits(['close', 'create']);

function getDefaultSnapshotName() {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `snap_${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
}

const snapshotName = ref(getDefaultSnapshotName());
const forAllProfiles = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close');
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown);
  await nextTick();
  inputRef.value?.focus();
  inputRef.value?.select();
});

onUnmounted(() => window.removeEventListener('keydown', handleKeyDown));
</script>

<template>
  <div
    @click.self="emit('close')"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
  >
    <div class="bg-slate-900 border border-slate-700 w-full max-w-md rounded-xl p-5 shadow-2xl">
      <h3 class="text-sm font-bold text-white mb-3">📸 Создать снапшот состояния</h3>

      <div class="space-y-3 mb-4">
        <div>
          <label class="text-xs text-slate-400 block mb-1">Название снапшота</label>
          <input
            ref="inputRef"
            v-model="snapshotName"
            type="text"
            placeholder="Например: Перед рефакторингом API"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
            @keydown.enter="snapshotName.trim() && emit('create', { name: snapshotName, forAll: forAllProfiles })"
          />
        </div>

        <div class="bg-slate-950/60 p-2.5 rounded border border-slate-800 space-y-1.5 text-xs">
          <label class="flex items-center gap-2 cursor-pointer text-slate-300">
            <input v-model="forAllProfiles" type="checkbox" class="accent-sky-500 rounded" />
            <span>Сохранить состояние для всех профилей</span>
          </label>
          <p class="text-[11px] text-slate-500">
            {{ forAllProfiles ? 'Будут зафиксированы файлы всех профилей проекта.' : `Только для текущего профиля (${activeProfileName}).` }}
          </p>
        </div>
      </div>

      <div class="flex justify-end gap-2">
        <button @click="emit('close')" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
        <button
          :disabled="!snapshotName.trim()"
          @click="emit('create', { name: snapshotName, forAll: forAllProfiles })"
          class="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-semibold text-xs px-4 py-1.5 rounded transition shadow"
        >
          Зафиксировать
        </button>
      </div>
    </div>
  </div>
</template>