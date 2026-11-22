import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { useProjectStore } from '../src/entities/projectStore';
import { api } from '../src/shared/api/client';
import ConfigHelpModal from '../src/widgets/ConfigHelpModal.vue';
import InstructionModal from '../src/widgets/InstructionModal.vue';
import AttachedFilesViewerModal from '../src/widgets/AttachedFilesViewerModal.vue';
import HistoryPanel from '../src/widgets/HistoryPanel/HistoryPanel.vue';
import App from '../src/App.vue';

describe('New Features: Config, Attached Viewer Search, Author Links', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(api, 'getProjects').mockResolvedValue([]);
    vi.spyOn(api, 'getFileContent').mockResolvedValue({ content: 'mock content', is_binary: false });
    vi.spyOn(api, 'getBackgroundSetting').mockResolvedValue({
      filename: 'background.png',
      background_url: '/images/background.png',
      enabled: true,
    });
    vi.spyOn(api, 'toggleBackground').mockResolvedValue({
      success: true,
      enabled: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('ConfigHelpModal renders config explanation and emits close', async () => {
    const wrapper = mount(ConfigHelpModal);
    expect(wrapper.text()).toContain('Что такое Конфигурация проекта?');
    expect(wrapper.text()).toContain('fs_orchestrator_config.json');
    expect(wrapper.text()).toContain('Загрузить конфигурацию');

    await wrapper.find('button.bg-sky-600').trigger('click');
    expect(wrapper.emitted('close')).toBeDefined();
  });

  it('AttachedFilesViewerModal filters files using substring, wildcards and regex', async () => {
    const store = useProjectStore();
    store.files = [
      { path: 'src/main.ts', name: 'main.ts', state: 'writable' },
      { path: 'src/utils/helper.py', name: 'helper.py', state: 'readonly' },
      { path: 'README.md', name: 'README.md', state: 'readonly' },
      { path: 'ignored.txt', name: 'ignored.txt', state: 'unmarked' },
    ];

    const wrapper = mount(AttachedFilesViewerModal);
    const input = wrapper.find('input[type="text"]');
    expect(input.exists()).toBe(true);

    // Изначально видны только 3 прикрепленных файла (writable/readonly)
    expect(wrapper.text()).toContain('src/main.ts');
    expect(wrapper.text()).toContain('src/utils/helper.py');
    expect(wrapper.text()).toContain('README.md');
    expect(wrapper.text()).not.toContain('ignored.txt');

    // Поиск по маске *.py
    await input.setValue('*.py');
    expect(wrapper.text()).toContain('src/utils/helper.py');
    expect(wrapper.text()).not.toContain('src/main.ts');
    expect(wrapper.text()).not.toContain('README.md');

    // Поиск по регулярке ^src/
    await input.setValue('^src/');
    expect(wrapper.text()).toContain('src/main.ts');
    expect(wrapper.text()).toContain('src/utils/helper.py');
    expect(wrapper.text()).not.toContain('README.md');

    // Поиск без совпадений
    await input.setValue('nonexistent_file_xyz');
    expect(wrapper.text()).toContain('Ничего не найдено по запросу');
  });

  it('App renders IDE menu bar, project folder button, left-aligned copyright and collapsed logs by default', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.profiles = [{ id: 1, project_id: 1, name: 'default', is_default: true }];
    store.currentProfile = store.profiles[0];

    const wrapper = mount(App);

    // Верхнее IDE-меню
    expect(wrapper.text()).toContain('Профиль');
    expect(wrapper.text()).toContain('Снапшоты');
    expect(wrapper.text()).toContain('Конфигурация');
    expect(wrapper.text()).toContain('Персонализация');

    // Кнопки внутри выпадающих списков
    expect(wrapper.text()).toContain('Новый профиль');
    expect(wrapper.text()).toContain('Удалить профиль');
    expect(wrapper.text()).toContain('Создать снапшот');
    expect(wrapper.text()).toContain('Загрузить снапшот');
    expect(wrapper.text()).toContain('Сохранить конфигурацию');
    expect(wrapper.text()).toContain('Загрузить конфигурацию');
    expect(wrapper.text()).toContain('Что такое конфигурация?');
    expect(wrapper.text()).toContain('Отображать фон');
    expect(wrapper.text()).toContain('Изменить фон');

    // Папка проекта в верхней панели (без эмодзи) и Изменить директорию в строке проекта
    expect(wrapper.text()).toContain('Изменить директорию');
    const folderBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Папка проекта');
    expect(folderBtn).toBeDefined();
    expect(folderBtn!.text()).toBe('Папка проекта');

    // Ссылки и прижатый влево копирайт
    const githubLink = wrapper.find('a[href="https://github.com/Doctorgth/FS-XML"]');
    const boostyLink = wrapper.find('a[href="https://boosty.to/doctorgth"]');

    expect(githubLink.exists()).toBe(true);
    expect(githubLink.text()).toContain('GitHub');
    expect(githubLink.classes()).toContain('bg-sky-500/20');
    expect(boostyLink.exists()).toBe(true);
    expect(boostyLink.text()).toContain('Boosty');
    expect(boostyLink.classes()).toContain('bg-orange-500/20');

    const copyrightEl = wrapper.find('.text-left.font-mono');
    expect(copyrightEl.exists()).toBe(true);
    expect(copyrightEl.text()).toContain('© Doctorgth 2026');

    // Лог работы по умолчанию свернут и разворачивается по кнопке
    const expandLogsBtn = wrapper.find('button[title="Развернуть лог работы"]');
    expect(expandLogsBtn.exists()).toBe(true);
    await expandLogsBtn.trigger('click');
    expect(wrapper.find('button[title="Свернуть лог работы"]').exists()).toBe(true);
  });

  it('App collapses and expands left panel via arrow button', async () => {
    const wrapper = mount(App);

    const collapseBtn = wrapper.find('button[title="Свернуть левую панель"]');
    expect(collapseBtn.exists()).toBe(true);
    await collapseBtn.trigger('click');

    expect(wrapper.find('button[title="Свернуть левую панель"]').exists()).toBe(false);
    const expandBtn = wrapper.find('button[title="Развернуть левую панель"]');
    expect(expandBtn.exists()).toBe(true);

    await expandBtn.trigger('click');
    expect(wrapper.find('button[title="Свернуть левую панель"]').exists()).toBe(true);
  });

  it('App shows custom modal instead of native alert when saving configuration', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };

    vi.spyOn(api, 'saveProjectConfig').mockResolvedValue({
      success: true,
      config_path: '/tmp/demo/fs_orchestrator_config.json',
    });

    const wrapper = mount(App);
    const saveBtn = wrapper.findAll('button').find((b) => b.text().includes('Сохранить конфигурацию'));
    expect(saveBtn).toBeDefined();
    await saveBtn!.trigger('click');

    await new Promise((r) => setTimeout(r, 0));
    expect(wrapper.text()).toContain('Конфигурация сохранена');
    expect(wrapper.text()).toContain('/tmp/demo/fs_orchestrator_config.json');
  });

  it('HistoryPanel renders ignoreTests checkbox with tooltip and emits updates', async () => {
    const wrapper = mount(HistoryPanel, {
      props: {
        allowManagement: false,
        includeUnmarked: false,
        ignoreTests: false,
      },
    });

    expect(wrapper.text()).toContain('Игнорировать тесты');
    const tooltipEl = wrapper.find('span[title*="test_ или _test"]');
    expect(tooltipEl.exists()).toBe(true);

    const checkboxes = wrapper.findAll('input[type="checkbox"]');
    expect(checkboxes.length).toBe(3);
    await checkboxes[2].setValue(true);

    expect(wrapper.emitted('update:ignoreTests')).toBeDefined();
    expect(wrapper.emitted('update:ignoreTests')![0]).toEqual([true]);
  });

  it('HistoryPanel opens custom modal for clearing history instead of native confirm', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'TestProj', root_dir: '/tmp/test', created_at: '2026-01-01' };
    store.history = [
      { id: 10, created_at: '2026-01-01T10:00:00', status: 'success', total_commands: 1, error_count: 0, profile_name: 'default' },
    ];

    const clearSpy = vi.spyOn(api, 'clearHistory').mockResolvedValue({ success: true });
    vi.spyOn(api, 'getHistory').mockResolvedValue([]);

    const wrapper = mount(HistoryPanel, {
      props: {
        allowManagement: false,
        includeUnmarked: false,
        ignoreTests: false,
      },
    });

    const clearBtn = wrapper.findAll('button').find((b) => b.text().includes('Очистить историю сессий'));
    expect(clearBtn).toBeDefined();
    await clearBtn!.trigger('click');

    expect(wrapper.text()).toContain('Очистка истории запусков');
    expect(wrapper.text()).toContain('TestProj');
    expect(clearSpy).not.toHaveBeenCalled();

    const confirmBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Очистить');
    expect(confirmBtn).toBeDefined();
    await confirmBtn!.trigger('click');

    expect(clearSpy).toHaveBeenCalledWith(1);
  });

  it('App uses background image from images folder, supports changing it via Personalization and has no backdrop-blur', async () => {
    const selectBgSpy = vi.spyOn(api, 'selectBackgroundImage').mockResolvedValue({
      selected: true,
      filename: 'new_wall.png',
      background_url: '/images/new_wall.png',
    });

    const wrapper = mount(App);
    const rootStyle = wrapper.attributes('style') || '';
    expect(rootStyle).toContain('images/background.png');
    expect(wrapper.html()).not.toContain('backdrop-blur');

    const changeBgBtn = wrapper.findAll('button').find((b) => b.text().includes('Изменить фон'));
    expect(changeBgBtn).toBeDefined();
    await changeBgBtn!.trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    expect(selectBgSpy).toHaveBeenCalled();
    expect(wrapper.attributes('style')).toContain('/images/new_wall.png');

    // Тест чекбокса «Отображать фон»
    const toggleBgSpy = vi.spyOn(api, 'toggleBackground').mockResolvedValue({ success: true, enabled: false });
    const bgCheckbox = wrapper.findAll('input[type="checkbox"]').find((el) => {
      return el.element.parentElement?.textContent?.includes('Отображать фон');
    });
    expect(bgCheckbox).toBeDefined();

    await bgCheckbox!.setValue(false);
    expect(toggleBgSpy).toHaveBeenCalledWith(false);
    expect(wrapper.attributes('style') || '').not.toContain('background-image');
  });

  it('App opens profiles list modal from Profile -> Delete Profile and asks confirmation before deletion', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.profiles = [
      { id: 1, project_id: 1, name: 'default', is_default: true },
      { id: 2, project_id: 1, name: 'FeatureA', is_default: false },
    ];
    store.currentProfile = store.profiles[0];

    const removeSpy = vi.spyOn(store, 'removeProfile').mockResolvedValue();

    const wrapper = mount(App);

    const openDeleteListBtn = wrapper.findAll('button').find((b) => b.text().includes('Удалить профиль'));
    expect(openDeleteListBtn).toBeDefined();
    await openDeleteListBtn!.trigger('click');

    expect(wrapper.text()).toContain('Управление профилями проекта');
    expect(wrapper.text()).toContain('FeatureA');
    expect(removeSpy).not.toHaveBeenCalled();

    const rowDeleteButtons = wrapper.findAll('button').filter((b) => b.text().trim() === 'Удалить');
    expect(rowDeleteButtons.length).toBeGreaterThanOrEqual(2);
    await rowDeleteButtons[1].trigger('click');

    expect(wrapper.text()).toContain('Удаление профиля');
    expect(wrapper.text()).toContain('"FeatureA"');
    expect(removeSpy).not.toHaveBeenCalled();

    const allDeleteBtns = wrapper.findAll('button').filter((b) => b.text().trim() === 'Удалить');
    await allDeleteBtns[allDeleteBtns.length - 1].trigger('click');

    expect(removeSpy).toHaveBeenCalledWith(2);
  });

  it('HistoryPanel animates prompt copy button without native alert', async () => {
    vi.spyOn(api, 'getSystemPrompt').mockResolvedValue({ prompt: 'FS-XML PROMPT' });
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    if (navigator.clipboard?.writeText) {
      vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    } else {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: vi.fn().mockResolvedValue(undefined) },
        configurable: true,
      });
    }

    const wrapper = mount(HistoryPanel, {
      props: {
        allowManagement: false,
        includeUnmarked: false,
        ignoreTests: false,
      },
    });

    const promptBtn = wrapper.findAll('button').find((b) => b.text().includes('КОПИРОВАТЬ ПРОМПТ'));
    expect(promptBtn).toBeDefined();
    await promptBtn!.trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    expect(alertSpy).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('СКОПИРОВАНО В БУФЕР!');
  });

  it('HistoryPanel saves context dump to project root without overwriting clipboard', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'DumpProj', root_dir: '/tmp/proj', created_at: '2026-01-01' };
    store.currentProfile = { id: 2, project_id: 1, name: 'default', is_default: true };

    vi.spyOn(api, 'getDump').mockResolvedValue({
      dump: 'DUMP CONTENT',
      dump_path: '/tmp/proj/context_dump.txt',
    });
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    if (navigator.clipboard?.writeText) {
      vi.spyOn(navigator.clipboard, 'writeText').mockImplementation(writeTextMock);
    } else {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        configurable: true,
      });
    }

    const wrapper = mount(HistoryPanel, {
      props: {
        allowManagement: false,
        includeUnmarked: false,
        ignoreTests: false,
      },
    });

    const dumpBtn = wrapper.findAll('button').find((b) => b.text().includes('СОЗДАТЬ ДАМП КОНТЕКСТА'));
    expect(dumpBtn).toBeDefined();
    await dumpBtn!.trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    expect(alertSpy).not.toHaveBeenCalled();
    expect(writeTextMock).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('Дамп контекста сохранен');
    expect(wrapper.text()).toContain('/tmp/proj/context_dump.txt');
    expect(wrapper.text()).not.toContain('буфер обмена');
  });

  it('App opens InstructionModal from top menu bar and explains pain points, prompt, Gemini and other models', async () => {
    const wrapper = mount(App);

    const instrBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Инструкция');
    expect(instrBtn).toBeDefined();
    await instrBtn!.trigger('click');

    expect(wrapper.text()).toContain('Инструкция по работе с программой');
    expect(wrapper.text()).toContain('Какую боль решает программа?');
    expect(wrapper.text()).toContain('миллионы токенов');
    expect(wrapper.text()).toContain('веб-чат');
    expect(wrapper.text()).toContain('не затирая ваш буфер обмена');
    expect(wrapper.text()).toContain('Профили — разграничение зон ответственности');
    expect(wrapper.text()).toContain('фронтенда ей ни к чему');
    expect(wrapper.text()).toContain('Снапшоты (контрольные точки)');
    expect(wrapper.text()).toContain('fs_orchestrator_config.json');
    expect(wrapper.text()).toContain('КОПИРОВАТЬ ПРОМПТ');
    expect(wrapper.text()).toContain('System Instructions');
    expect(wrapper.text()).toContain('Gemini');
    expect(wrapper.text()).toContain('другими моделями');

    const closeBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Понятно');
    expect(closeBtn).toBeDefined();
    await closeBtn!.trigger('click');

    expect(wrapper.findComponent(InstructionModal).exists()).toBe(false);
  });
});