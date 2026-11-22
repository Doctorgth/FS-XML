<script setup lang="ts">
import { ref } from 'vue';
import { useProjectStore } from '../../entities/projectStore';
import { api } from '../../shared/api/client';

const props = defineProps<{
  allowManagement: boolean;
}>();

const emit = defineEmits<{
  (e: 'status-change', status: 'idle' | 'success' | 'error'): void;
}>();

const store = useProjectStore();

const xmlInput = ref('');
const executionLoading = ref(false);
const executionStatus = ref<'idle' | 'success' | 'error'>('idle');
const statusText = ref('');

function setStatus(status: 'idle' | 'success' | 'error') {
  executionStatus.value = status;
  emit('status-change', status);
}

async function runExecution() {
  if (!store.currentProject || !store.currentProfile || !xmlInput.value.trim()) return;
  executionLoading.value = true;
  setStatus('idle');
  statusText.value = 'Применение...';

  try {
    const res = await api.executeXml(
      store.currentProject.id,
      store.currentProfile.id,
      xmlInput.value,
      props.allowManagement
    );
    await store.loadHistory();
    await store.selectProfile(store.currentProfile);

    if (res.error_count === 0 && res.total_commands > 0) {
      setStatus('success');
      statusText.value = `УСПЕШНО ПРИМЕНЕНО (${res.total_commands} команд)`;
      store.addLog(`Сессия #${res.session_id}: Все команды выполнены успешно (${res.total_commands})`);
    } else {
      setStatus('error');
      statusText.value = res.total_commands === 0
        ? 'ОШИБКА: Команды не распознаны'
        : `ОШИБКА ПРИМЕНЕНИЯ: ${res.error_count} из ${res.total_commands}`;
      store.addLog(
        res.total_commands === 0
          ? `Сессия #${res.session_id}: XML-команды не найдены`
          : `Сессия #${res.session_id}: Ошибок: ${res.error_count} из ${res.total_commands}`
      );
      for (const item of res.results) {
        if (!item.success) {
          store.addLog(`[Ошибка ${item.tag}] ${item.target_path || ''}: ${item.message}`);
        }
      }
    }
  } catch (err: any) {
    setStatus('error');
    statusText.value = `ОШИБКА ПРИМЕНЕНИЯ: ${err.message}`;
    store.addLog(`Критическая ошибка: ${err.message}`);
  } finally {
    executionLoading.value = false;
  }
}

function clearField() {
  xmlInput.value = '';
  setStatus('idle');
  statusText.value = '';
}

defineExpose({ runExecution, clearField, executionStatus });
</script>

<template>
  <div class="flex-1 flex flex-col h-full bg-transparent overflow-hidden">
    <!-- Поле ввода XML -->
    <div class="flex-1 flex flex-col p-3 min-h-[220px]">
      <textarea
        v-model="xmlInput"
        placeholder="Вставьте сюда XML-код замен от нейросети..."
        class="w-full flex-1 bg-slate-950/45 border border-slate-700/60 rounded-lg p-3 text-slate-100 placeholder:text-slate-400 font-mono text-xs focus:outline-none focus:border-sky-500 resize-none shadow-inner"
      ></textarea>
    </div>
  </div>
</template>