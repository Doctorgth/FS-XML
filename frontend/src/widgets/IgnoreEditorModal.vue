<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

const props = defineProps<{
  title: string;
  initialContent: string;
}>();

const emit = defineEmits(['close', 'save']);
const textContent = ref(props.initialContent);

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close');
}

onMounted(() => window.addEventListener('keydown', handleKeyDown));
onUnmounted(() => window.removeEventListener('keydown', handleKeyDown));
</script>

<template>
  <div
    @click.self="emit('close')"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 select-none"
  >
    <div class="bg-slate-900 border border-slate-700 w-full max-w-2xl h-[70vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
      <div class="px-5 py-3.5 border-b border-slate-800 flex justify-between items-center bg-slate-950">
        <h3 class="text-sm font-bold text-white tracking-wide">{{ title }}</h3>
        <button @click="emit('close')" class="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800">
          Закрыть
        </button>
      </div>

      <div class="flex-1 p-3 bg-slate-950">
        <textarea
          v-model="textContent"
          placeholder="Правила игнорирования (синтаксис .gitignore: *.log, node_modules/)..."
          class="w-full h-full bg-slate-900 border border-slate-800 rounded p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-sky-500 resize-none"
        ></textarea>
      </div>

      <div class="px-5 py-3 border-t border-slate-800 bg-slate-950 flex justify-end gap-2">
        <button @click="emit('close')" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white">Отмена</button>
        <button
          @click="emit('save', textContent)"
          class="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs px-4 py-1.5 rounded transition shadow"
        >
          Сохранить изменения
        </button>
      </div>
    </div>
  </div>
</template>