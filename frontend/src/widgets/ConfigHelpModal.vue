<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';

const emit = defineEmits(['close']);

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
    <div class="bg-slate-900 border border-slate-700 w-full max-w-lg rounded-xl p-5 shadow-2xl">
      <div class="flex items-center gap-2 mb-3">
        <span class="text-sky-400 font-bold text-base">⚙</span>
        <h3 class="text-sm font-bold text-white tracking-wide">Что такое Конфигурация проекта?</h3>
      </div>

      <div class="space-y-3 text-xs text-slate-300 leading-relaxed">
        <p>
          <strong>Конфигурация проекта</strong> — это JSON-файл (<code class="text-amber-300 font-mono">fs_orchestrator_config.json</code>), сохраняемый в корневую папку проекта.
        </p>
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
          <div>
            <strong class="text-sky-300">Что хранится внутри:</strong>
            <p class="text-slate-400 text-[11px] mt-0.5">
              Название проекта, все его профили и настроенные права доступа к файлам (<strong>Writable</strong> и <strong>Read-Only</strong>).
            </p>
          </div>
          <div>
            <strong class="text-emerald-300">Зачем это нужно:</strong>
            <p class="text-slate-400 text-[11px] mt-0.5">
              Чтобы поделиться проектом с другом или перенести работу на другой ПК. Достаточно скинуть папку с проектом и этим JSON-файлом — при нажатии <strong>«Загрузить конфигурацию»</strong> программа сразу создаст проект, все профили и права на файлы.
            </p>
          </div>
        </div>
      </div>

      <div class="mt-5 flex justify-end">
        <button @click="emit('close')" class="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs px-4 py-1.5 rounded transition shadow">
          Понятно
        </button>
      </div>
    </div>
  </div>
</template>