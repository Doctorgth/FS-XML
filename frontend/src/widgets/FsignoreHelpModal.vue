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
    <div class="bg-slate-900 border border-slate-700 w-full max-w-2xl max-h-[85vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
      <!-- Заголовок -->
      <div class="px-5 py-3.5 border-b border-slate-800 flex justify-between items-center bg-slate-950">
        <div class="flex items-center gap-2">
          <span class="text-amber-400 font-bold">ℹ</span>
          <h3 class="text-sm font-bold text-white tracking-wide">Справка: Как работает и на что влияет fsignore?</h3>
        </div>
        <button @click="emit('close')" class="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800">
          Закрыть (Esc)
        </button>
      </div>

      <!-- Содержимое справки -->
      <div class="flex-1 overflow-y-auto p-5 space-y-4 text-xs text-slate-300 leading-relaxed">
        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800">
          <h4 class="font-bold text-sky-400 mb-1.5 uppercase text-[11px] tracking-wider">🎯 На что влияет игнор-лист:</h4>
          <ul class="list-disc list-inside space-y-1 text-slate-300">
            <li><strong class="text-white">Дерево файлов:</strong> Игнорируемые файлы и папки вообще не отображаются в окне выбора контекста.</li>
            <li><strong class="text-white">Поиск по проекту:</strong> Сканирование полностью обходит стороной игнорируемые ресурсы.</li>
            <li><strong class="text-white">Контекстный дамп для ИИ:</strong> Никакие файлы из игнора не попадут в промпт (ни текстом, ни путем).</li>
            <li><strong class="text-white">Защита от зависаний:</strong> Исключает чтение гигантских служебных директорий (например, <code class="text-amber-300 font-mono">node_modules/</code> на 30 000+ файлов).</li>
          </ul>
        </section>

        <section class="grid grid-cols-2 gap-3">
          <div class="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
            <h5 class="font-bold text-amber-300 mb-1">📁 Проектный .fsignore</h5>
            <p class="text-slate-400 text-[11px]">
              Хранится в корне конкретного открытого проекта (<code class="text-slate-200 font-mono">.fsignore</code>). Применяется только к нему (например, временные дампы базы или локальные кэши сборщика).
            </p>
          </div>
          <div class="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
            <h5 class="font-bold text-sky-300 mb-1">🌐 Глобальный fsignore</h5>
            <p class="text-slate-400 text-[11px]">
              Хранится в корне самой программы (<code class="text-slate-200 font-mono">fsignore_global</code>). Действует на <strong>все</strong> проекты автоматически (<code class="text-slate-200 font-mono">.git, .venv, node_modules</code>).
            </p>
          </div>
        </section>

        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800">
          <h4 class="font-bold text-emerald-400 mb-1.5 uppercase text-[11px] tracking-wider">📝 Правила синтаксиса (как в .gitignore):</h4>
          <div class="font-mono text-[11px] bg-slate-900 p-2.5 rounded border border-slate-800 space-y-1 text-slate-300">
            <div><span class="text-slate-500"># Это однострочный комментарий</span></div>
            <div>node_modules/ <span class="text-slate-500"># Игнорировать всю папку со всеми подпапками</span></div>
            <div>*.log <span class="text-slate-500"># Игнорировать все файлы с расширением .log</span></div>
            <div>temp_* <span class="text-slate-500"># Игнорировать любые файлы, начинающиеся с temp_</span></div>
            <div>dist/ <span class="text-slate-500"># Папка артефактов сборки</span></div>
            <div>.venv/ <span class="text-slate-500"># Окружение Python</span></div>
          </div>
          <p class="mt-2 text-slate-400 text-[11px]">
            Комментарии начинаются со знака <code class="text-sky-300 font-bold">#</code>. Пустые строки и пробелы вокруг правил игнорируются автоматически.
          </p>
        </section>
      </div>

      <div class="px-5 py-3 border-t border-slate-800 bg-slate-950 flex justify-end">
        <button @click="emit('close')" class="bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs px-5 py-1.5 rounded transition shadow">
          Понятно
        </button>
      </div>
    </div>
  </div>
</template>