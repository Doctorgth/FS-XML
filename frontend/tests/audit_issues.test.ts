import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { useProjectStore } from '../src/entities/projectStore';
import { api } from '../src/shared/api/client';
import FileTreeModal from '../src/widgets/FileTree/FileTreeModal.vue';
import ExecutionHub from '../src/widgets/ExecutionHub/ExecutionHub.vue';
import HistoryPanel from '../src/widgets/HistoryPanel/HistoryPanel.vue';
import AttachedFilesViewerModal from '../src/widgets/AttachedFilesViewerModal.vue';
import CreateSnapshotModal from '../src/widgets/CreateSnapshotModal.vue';
import SnapshotsListModal from '../src/widgets/SnapshotsListModal.vue';
import App from '../src/App.vue';

describe('Audit Issues Regression & Tracking Tests', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(api, 'getProjects').mockResolvedValue([]);
    vi.spyOn(api, 'getBackgroundSetting').mockResolvedValue({
      filename: 'background.png',
      background_url: '/images/background.png',
      enabled: true,
    });
    vi.spyOn(api, 'toggleBackground').mockResolvedValue({ success: true, enabled: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // 2.3 Поиск со спецсимволами RegExp и маской * не должен ронять FileTreeModal
  it('Audit 2.3: FileTreeModal handles wildcard search with regex metacharacters safely', async () => {
    const store = useProjectStore();
    store.currentProfile = { id: 1, project_id: 1, name: 'default', is_default: true };
    store.files = [
      { path: 'src/file[1].ts', name: 'file[1].ts', state: 'unmarked' },
      { path: 'src/app.ts', name: 'app.ts', state: 'unmarked' },
    ];

    const wrapper = mount(FileTreeModal);
    const searchInput = wrapper.find('input[type="text"]');

    await searchInput.setValue('file[1]*.ts');
    // Без Enter / кнопки Поиск перерисовка поиска ещё не применяется
    expect(wrapper.text()).not.toContain('file[1].ts');

    await searchInput.trigger('keydown.enter');
    expect(wrapper.text()).toContain('file[1].ts');
    expect(wrapper.text()).not.toContain('app.ts');

    await searchInput.setValue('(test)*.py');
    const searchBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Поиск');
    expect(searchBtn).toBeDefined();
    await searchBtn!.trigger('click');

    await searchInput.setValue('a+*.txt');
    await searchInput.trigger('keydown.enter');
    expect(wrapper.find('input[type="text"]').exists()).toBe(true);
  });

  // 2.5 ExecutionHub не должен показывать status="success", если total_commands === 0
  it('Audit 2.5: ExecutionHub emits error instead of success when 0 commands were executed', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.currentProfile = { id: 1, project_id: 1, name: 'default', is_default: true };

    vi.spyOn(api, 'executeXml').mockResolvedValue({
      session_id: 10,
      status: 'success',
      total_commands: 0,
      error_count: 0,
      results: [],
    });
    vi.spyOn(api, 'getHistory').mockResolvedValue([]);
    vi.spyOn(api, 'getFiles').mockResolvedValue([]);

    const wrapper = mount(ExecutionHub, {
      props: { allowManagement: false },
    });

    await wrapper.find('textarea').setValue('plain text without valid commands');
    await (wrapper.vm as any).runExecution();
    await new Promise((r) => setTimeout(r, 0));

    const emitted = wrapper.emitted('status-change') || [];
    const lastStatus = emitted[emitted.length - 1]?.[0];
    expect(lastStatus).toBe('error');
  });

  // 1.1 Кнопка «Откатить» не должна показываться для управляющих команд без снимков
  it('Audit 1.1: HistoryPanel hides Rollback button for management commands without file snapshot', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.history = [
      {
        id: 1,
        created_at: '2026-01-01T12:00:00',
        status: 'success',
        total_commands: 2,
        error_count: 0,
        profile_name: 'default',
      },
    ];

    vi.spyOn(api, 'getSessionDetails').mockResolvedValue([
      {
        id: 101,
        session_id: 1,
        command_tag: 'fs_file_state',
        target_path: 'secret.py',
        status: 'success',
        error_details: null,
        original_snapshot: null,
        new_snapshot: null,
      },
      {
        id: 102,
        session_id: 1,
        command_tag: 'fs_edit',
        target_path: 'main.py',
        status: 'success',
        error_details: null,
        original_snapshot: 'v1',
        new_snapshot: 'v2',
      },
    ]);

    const wrapper = mount(HistoryPanel, {
      props: { allowManagement: true, includeUnmarked: false, ignoreTests: false },
    });

    // Раскрываем сессию
    const sessionHeader = wrapper.find('.cursor-pointer');
    await sessionHeader.trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    const rollbackButtons = wrapper
      .findAll('button')
      .filter((b) => b.text().trim() === 'Откатить');
    expect(rollbackButtons.length).toBe(1);
  });

  // 3.4 Записи со статусом rolled_back не должны подсвечиваться как красные ошибки
  it('Audit 3.4: HistoryPanel does not style rolled_back records with error rose background', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.history = [
      {
        id: 2,
        created_at: '2026-01-01T12:00:00',
        status: 'success',
        total_commands: 1,
        error_count: 0,
        profile_name: 'default',
      },
    ];

    vi.spyOn(api, 'getSessionDetails').mockResolvedValue([
      {
        id: 201,
        session_id: 2,
        command_tag: 'fs_edit',
        target_path: 'app.py',
        status: 'rolled_back',
        error_details: null,
        original_snapshot: 'v1',
        new_snapshot: 'v2',
      },
    ]);

    const wrapper = mount(HistoryPanel, {
      props: { allowManagement: false, includeUnmarked: false, ignoreTests: false },
    });

    await wrapper.find('.cursor-pointer').trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    const row = wrapper.findAll('.font-mono').find((el) => el.text().includes('app.py'));
    expect(row).toBeDefined();
    expect(row!.classes().join(' ')).not.toContain('bg-rose-950/40');
  });

  // 3.4 Создание снапшота в App.vue не должно вызывать нативный alert(), а клик по hovered меню не должен его закрывать
  it('Audit 3.4: App avoids native alert on snapshot creation, reloads profiles on restore, and keeps menu open on hover+click', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.profiles = [{ id: 1, project_id: 1, name: 'default', is_default: true }];
    store.currentProfile = store.profiles[0];

    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    vi.spyOn(api, 'createSnapshot').mockResolvedValue({ success: true, id: 5 });
    const getProfilesSpy = vi.spyOn(api, 'getProfiles').mockResolvedValue(store.profiles);
    vi.spyOn(api, 'getFiles').mockResolvedValue([]);
    vi.spyOn(api, 'getHistory').mockResolvedValue([]);
    vi.spyOn(api, 'getSnapshots').mockResolvedValue([
      { id: 5, name: 's1', created_at: '2026-01-01', profile_name: 'default' },
    ]);

    const wrapper = mount(App);

    // Проверка hover + click на пункте меню "Профиль"
    const profileBtn = wrapper.findAll('button').find((b) => b.text().trim() === 'Профиль');
    expect(profileBtn).toBeDefined();
    const menuWrapper = profileBtn!.element.parentElement!;
    await profileBtn!.trigger('mouseenter');
    await profileBtn!.trigger('click');
    const dropdown = menuWrapper.querySelector('div.absolute') as HTMLElement | null;
    expect(dropdown).not.toBeNull();
    expect(dropdown!.style.display).not.toBe('none');

    // Проверка создания снапшота без native alert()
    const createSnapBtn = wrapper.findAll('button').find((b) => b.text().includes('Создать снапшот'));
    await createSnapBtn!.trigger('click');
    const modal = wrapper.findComponent(CreateSnapshotModal);
    expect(modal.exists()).toBe(true);
    modal.vm.$emit('create', { name: 'snap_test', forAll: false });
    await new Promise((r) => setTimeout(r, 0));
    expect(alertSpy).not.toHaveBeenCalled();

    // Проверка перезагрузки профилей после восстановления снапшота
    const loadSnapBtn = wrapper.findAll('button').find((b) => b.text().includes('Загрузить снапшот'));
    await loadSnapBtn!.trigger('click');
    const listModal = wrapper.findComponent(SnapshotsListModal);
    expect(listModal.exists()).toBe(true);
    listModal.vm.$emit('restored');
    await new Promise((r) => setTimeout(r, 0));
    expect(getProfilesSpy).toHaveBeenCalled();
  });

  // 3.4 Race condition при быстром переключении файлов в AttachedFilesViewerModal
  it('Audit 3.4: AttachedFilesViewerModal ignores stale async response when switching files quickly', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'Demo', root_dir: '/tmp/demo', created_at: '2026-01-01' };
    store.files = [
      { path: 'slow.ts', name: 'slow.ts', state: 'writable' },
      { path: 'fast.ts', name: 'fast.ts', state: 'writable' },
    ];

    let resolveSlow!: (val: { content: string; is_binary: boolean }) => void;
    const slowPromise = new Promise<{ content: string; is_binary: boolean }>((res) => {
      resolveSlow = res;
    });

    vi.spyOn(api, 'getFileContent').mockImplementation((_projId, relPath) => {
      if (relPath === 'slow.ts') return slowPromise;
      return Promise.resolve({ content: 'FAST_CONTENT', is_binary: false });
    });

    const wrapper = mount(AttachedFilesViewerModal);
    // Изначально выбирается slow.ts, сразу переключаемся на fast.ts
    const fastItem = wrapper.findAll('div.cursor-pointer').find((el) => el.text().includes('fast.ts'));
    expect(fastItem).toBeDefined();
    await fastItem!.trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    expect(wrapper.text()).toContain('FAST_CONTENT');

    // Теперь с задержкой приходит ответ для slow.ts — он НЕ должен перезаписать FAST_CONTENT
    resolveSlow({ content: 'STALE_SLOW_CONTENT', is_binary: false });
    await new Promise((r) => setTimeout(r, 0));

    expect(wrapper.text()).toContain('FAST_CONTENT');
    expect(wrapper.text()).not.toContain('STALE_SLOW_CONTENT');
  });

  it('Audit extra: removeProject clears profiles & history and HistoryPanel handles session load errors', async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: 'LastProj', root_dir: '/tmp/last', created_at: '2026-01-01' };
    store.profiles = [{ id: 1, project_id: 1, name: 'default', is_default: true }];
    store.currentProfile = store.profiles[0];
    store.history = [
      { id: 10, created_at: '2026-01-01 12:00:00', status: 'success', total_commands: 1, error_count: 0, profile_name: 'default' },
    ];

    vi.spyOn(api, 'deleteProject').mockResolvedValue({ success: true });
    vi.spyOn(api, 'getProjects').mockResolvedValue([]);

    await store.removeProject(1);
    expect(store.currentProject).toBeNull();
    expect(store.profiles).toEqual([]);
    expect(store.history).toEqual([]);

    // HistoryPanel error state instead of infinite loading
    store.currentProject = { id: 2, name: 'ErrProj', root_dir: '/tmp/err', created_at: '2026-01-01' };
    store.history = [
      { id: 20, created_at: '2026-01-01 12:00:00', status: 'success', total_commands: 1, error_count: 0, profile_name: 'default' },
    ];
    vi.spyOn(api, 'getSessionDetails').mockRejectedValueOnce(new Error('Network fail'));

    const hp = mount(HistoryPanel, {
      props: { allowManagement: false, includeUnmarked: false, ignoreTests: false },
    });
    await hp.find('.cursor-pointer').trigger('click');
    await new Promise((r) => setTimeout(r, 0));

    expect(hp.text()).toContain('Network fail');
    expect(hp.text()).toContain('Повторить');
  });
});