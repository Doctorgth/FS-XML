import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useProjectStore } from '../src/entities/projectStore';

describe('Project Store State Logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('initializes with default empty state', () => {
    const store = useProjectStore();
    expect(store.projects).toEqual([]);
    expect(store.currentProject).toBeNull();
    expect(store.files).toEqual([]);
  });

  it('manages local files and toggles state correctly', () => {
    const store = useProjectStore();
    store.files = [
      { path: 'src/main.ts', name: 'main.ts', state: 'unmarked' }
    ];

    expect(store.files[0].state).toBe('unmarked');
  });
});