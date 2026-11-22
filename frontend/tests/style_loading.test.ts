import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('CSS and Tailwind Configuration Verification', () => {
  it('style.css exists and contains Tailwind directives', () => {
    const stylePath = path.resolve(__dirname, '../src/style.css');
    expect(fs.existsSync(stylePath)).toBe(true);

    const content = fs.readFileSync(stylePath, 'utf-8');
    expect(content).toContain('@tailwind base;');
    expect(content).toContain('@tailwind components;');
    expect(content).toContain('@tailwind utilities;');
  });

  it('main.ts correctly imports style.css', () => {
    const mainPath = path.resolve(__dirname, '../src/main.ts');
    expect(fs.existsSync(mainPath)).toBe(true);

    const content = fs.readFileSync(mainPath, 'utf-8');
    expect(content).toMatch(/import\s+['"]\.\/style\.css['"]/);
  });

  it('tailwind.config targets all Vue components', () => {
    const candidates = [
      path.resolve(__dirname, '../tailwind.config.js'),
      path.resolve(__dirname, '../tailwind.config.ts'),
      path.resolve(__dirname, '../tailwind.config.cjs'),
    ];

    const twPath = candidates.find((p) => fs.existsSync(p));
    expect(twPath, 'Tailwind config file must exist').toBeDefined();

    if (twPath) {
      const content = fs.readFileSync(twPath, 'utf-8');
      expect(content).toContain('./src/**/*.{vue,js,ts,jsx,tsx}');
    }
  });
});