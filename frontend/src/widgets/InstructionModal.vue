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
          <span class="text-sky-400 font-bold text-base">📘</span>
          <h3 class="text-sm font-bold text-white tracking-wide">Инструкция по работе с программой</h3>
        </div>
        <button @click="emit('close')" class="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800">
          Закрыть (Esc)
        </button>
      </div>

      <!-- Содержимое -->
      <div class="flex-1 overflow-y-auto p-5 space-y-4 text-xs text-slate-300 leading-relaxed">
        <!-- Какую боль решает программа -->
        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-rose-900/50 space-y-2.5">
          <h4 class="font-bold text-rose-400 uppercase text-[11px] tracking-wider">🔥 Какую боль решает программа?</h4>

          <div class="space-y-2">
            <div>
              <strong class="text-white">1. Бесконтрольные AI-агенты и сжигание токенов по API:</strong>
              <p class="text-slate-300 mt-0.5">
                Обычный агент (вроде Grok и аналогов) сам решает, что читать, лазит по всему проекту, вносит правки куда попало и при работе через API сжигает миллионы токенов на лишние чтения файлов.
                Здесь <strong>вы сами жёстко задаёте границы</strong>: только выбранные файлы попадают в контекст, причём <strong class="text-sky-300">Writable</strong> можно менять, а <strong class="text-amber-300">Read-Only</strong> — строго только для чтения. Лишних чтений и случайных правок больше нет.
              </p>
            </div>

            <div>
              <strong class="text-white">2. Удобная работа в обычном веб-чате с нейросетями:</strong>
              <p class="text-slate-300 mt-0.5">
                В веб-чатах у нейросети нет прямого доступа к файловой системе, но при этом <strong>большие лимиты контекста, которые не зависят от числа токенов</strong>.
                С <code class="text-sky-300 font-mono">FS-XML</code> вам не нужно руками копировать десятки файлов и разносить правки по коду: вы в один клик собираете чистый <code class="text-amber-300 font-mono">context_dump.txt</code>, прикрепляете его в чат, а готовый XML-ответ применяете одной кнопкой с историей и откатом.
              </p>
            </div>
          </div>
        </section>

        <!-- Системный промпт -->
        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800 space-y-2">
          <h4 class="font-bold text-amber-400 uppercase text-[11px] tracking-wider">🤖 Системный промпт для нейросети</h4>
          <p>
            Чтобы нейросеть понимала, в каком формате выдавать изменения файлов (<code class="text-sky-300 font-mono">&lt;fs_edit&gt;</code>, <code class="text-sky-300 font-mono">&lt;fs_create&gt;</code>), ей обязательно нужно передать <strong>системный промпт</strong>:
          </p>
          <ul class="list-disc list-inside space-y-1 text-slate-300">
            <li>
              <strong class="text-white">Откуда брать:</strong> нажмите кнопку <span class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-semibold">КОПИРОВАТЬ ПРОМПТ</span> в правой нижней части окна программы (он берется из файла <code class="text-amber-300 font-mono">FS-XML.txt</code>).
            </li>
            <li>
              <strong class="text-white">Куда вставлять:</strong> вставьте скопированный текст в поле <strong>System Instructions</strong> (Системная инструкция в Google AI Studio / API) или <strong>просто отправьте в чат</strong> в начале диалога с нейросетью.
            </li>
          </ul>
        </section>

        <!-- Пошаговый порядок работы -->
        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800">
          <h4 class="font-bold text-emerald-400 mb-2 uppercase text-[11px] tracking-wider">🛠 Как пользоваться (пошагово):</h4>
          <ol class="list-decimal list-inside space-y-1.5 text-slate-300">
            <li>
              <strong class="text-white">Добавьте проект:</strong> нажмите <span class="text-sky-400 font-semibold">+ Новый проект</span> в левой панели и укажите папку с вашим кодом.
            </li>
            <li>
              <strong class="text-white">Выберите файлы контекста:</strong> в правой панели нажмите <span class="text-slate-200 font-semibold">Редактировать</span> и пометьте нужные файлы как <strong class="text-sky-400">W (Writable)</strong> — разрешено редактировать, или <strong class="text-amber-400">RO (Read-Only)</strong> — только для чтения (ИИ увидит код, но не сможет его менять).
            </li>
            <li>
              <strong class="text-white">Передайте промпт и дамп нейросети:</strong> скопируйте системный промпт (<span class="text-slate-200 font-semibold">КОПИРОВАТЬ ПРОМПТ</span>), затем нажмите <span class="text-sky-400 font-semibold">СОЗДАТЬ ДАМП КОНТЕКСТА</span> — дамп сохранится в файл <code class="text-amber-300 font-mono">context_dump.txt</code> в корне проекта, <strong>не затирая ваш буфер обмена</strong>. Прикрепите этот файл к чату и напишите задачу.
            </li>
            <li>
              <strong class="text-white">Примените изменения:</strong> скопируйте XML-ответ нейросети, вставьте в центральное текстовое поле и нажмите <span class="text-sky-400 font-semibold">ВЫПОЛНИТЬ ЗАМЕНУ</span>.
            </li>
            <li>
              <strong class="text-white">Контроль и откат:</strong> в правой панели истории можно откатить любую правку, а через меню <span class="text-slate-200 font-semibold">Снапшоты</span> — сохранить контрольную точку проекта перед крупным рефакторингом.
            </li>
          </ol>
        </section>

        <!-- Профили, Снапшоты и Конфигурация -->
        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800 space-y-2.5">
          <h4 class="font-bold text-cyan-400 uppercase text-[11px] tracking-wider">🧩 Профили, Снапшоты и Конфигурация</h4>

          <div class="space-y-2">
            <div>
              <strong class="text-amber-300">Профили — разграничение зон ответственности:</strong>
              <p class="text-slate-300 mt-0.5">
                Профиль хранит свой независимый набор разрешений (<strong class="text-sky-300">Writable</strong> / <strong class="text-amber-300">Read-Only</strong>) для файлов проекта.
                Разные профили позволяют дополнительно разграничить нейросеть: например, если мы вносим изменения в <strong>бэкенд</strong>, то выбираем профиль для бэкенда — нейронка ответственна только за серверную часть с изолированными критическими файлами (они либо в <strong class="text-amber-300">Read-Only</strong>, либо не отмечены), а сжигать лишние токены на файлы фронтенда ей ни к чему.
              </p>
            </div>

            <div>
              <strong class="text-emerald-300">Снапшоты (контрольные точки):</strong>
              <p class="text-slate-300 mt-0.5">
                Моментальный снимок содержимого отмеченных файлов и настроек профилей. Создавайте снапшот перед сложным рефакторингом — если нейросеть сломает логику, проект можно откатить к идеальному состоянию в один клик (меню <strong>Снапшоты</strong>).
              </p>
            </div>

            <div>
              <strong class="text-sky-300">Конфигурация (<code class="text-amber-300 font-mono">fs_orchestrator_config.json</code>):</strong>
              <p class="text-slate-300 mt-0.5">
                Файл с настройками проекта, всеми его профилями и правами доступа к файлам. Позволяет сохранить разметку в корень проекта, чтобы перенести её на другой ПК или поделиться готовой настройкой с другом (меню <strong>Конфигурация</strong>).
              </p>
            </div>
          </div>
        </section>

        <!-- Совместимость с моделями -->
        <section class="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800">
          <h4 class="font-bold text-purple-400 mb-1 uppercase text-[11px] tracking-wider">✨ Поддерживаемые нейросети</h4>
          <p class="text-slate-300">
            Программа изначально разрабатывалась под <strong>Gemini</strong> (Google AI Studio / Gemini), но формат <code class="text-sky-300 font-mono">FS-XML</code> универсален — он также отлично работает с другими моделями (<strong>ChatGPT / GPT</strong>, <strong>Claude</strong>, <strong>DeepSeek</strong>, <strong>Qwen</strong> и др.), которым можно передать текстовый системный промпт.
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