import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ExecutionHub from '../src/widgets/ExecutionHub/ExecutionHub.vue';
import HistoryPanel from '../src/widgets/HistoryPanel/HistoryPanel.vue';

describe('UI Widgets Rendering', () => {
  setActivePinia(createPinia());

  it('ExecutionHub renders textarea for XML input', () => {
    const wrapper = mount(ExecutionHub, {
      props: {
        allowManagement: false,
      },
    });

    expect(wrapper.find('textarea').exists()).toBe(true);
    expect(wrapper.find('textarea').attributes('placeholder')).toContain('XML-код');
  });

  it('HistoryPanel renders controls, fsignore buttons and empty state', () => {
    const wrapper = mount(HistoryPanel, {
      props: {
        allowManagement: false,
        includeUnmarked: false,
      },
    });

    expect(wrapper.text()).toContain('История запусков');
    expect(wrapper.text()).toContain('История запусков пуста');
    expect(wrapper.text()).toContain('Управляющие команды');
    expect(wrapper.text()).toContain('Имена неотмеченных файлов');
    expect(wrapper.text()).toContain('Игнорировать тесты');
    expect(wrapper.text()).toContain('Проектный fsignore');
    expect(wrapper.text()).toContain('Глобальный fsignore');
    expect(wrapper.text()).toContain('СОЗДАТЬ ДАМП КОНТЕКСТА');
  });
});