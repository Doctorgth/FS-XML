import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import CreateSnapshotModal from '../src/widgets/CreateSnapshotModal.vue';
import SnapshotHelpModal from '../src/widgets/SnapshotHelpModal.vue';
import FsignoreHelpModal from '../src/widgets/FsignoreHelpModal.vue';
import IgnoreEditorModal from '../src/widgets/IgnoreEditorModal.vue';

describe('V2 Modals and Features Rendering', () => {
  it('CreateSnapshotModal renders input and emits create event', async () => {
    const wrapper = mount(CreateSnapshotModal, {
      props: { activeProfileName: 'default' },
    });

    expect(wrapper.text()).toContain('Создать снапшот состояния');
    expect(wrapper.text()).toContain('Только для текущего профиля (default)');

    const input = wrapper.find('input[type="text"]');
    expect((input.element as HTMLInputElement).value).toMatch(/^snap_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}$/);
    await input.setValue('TestSnapshot');

    const button = wrapper.find('button.bg-sky-600');
    expect(button.attributes('disabled')).toBeUndefined();
    await button.trigger('click');

    expect(wrapper.emitted('create')).toBeDefined();
    expect(wrapper.emitted('create')![0]).toEqual([{ name: 'TestSnapshot', forAll: false }]);
  });

  it('SnapshotHelpModal renders description and close button', () => {
    const wrapper = mount(SnapshotHelpModal);
    expect(wrapper.text()).toContain('Что такое Снапшот проекта?');
    expect(wrapper.text()).toContain('контрольная точка');
  });

  it('FsignoreHelpModal renders .gitignore syntax reference', () => {
    const wrapper = mount(FsignoreHelpModal);
    expect(wrapper.text()).toContain('Как работает и на что влияет fsignore?');
    expect(wrapper.text()).toContain('node_modules/');
    expect(wrapper.text()).toContain('*.log');
  });

  it('IgnoreEditorModal binds content and emits save', async () => {
    const wrapper = mount(IgnoreEditorModal, {
      props: {
        title: 'Тест игнора',
        initialContent: 'temp_*\n# comment',
      },
    });

    const textarea = wrapper.find('textarea');
    expect(textarea.element.value).toContain('temp_*');

    await textarea.setValue('new_rule/');
    await wrapper.find('button.bg-sky-600').trigger('click');

    expect(wrapper.emitted('save')).toBeDefined();
    expect(wrapper.emitted('save')![0]).toEqual(['new_rule/']);
  });
});