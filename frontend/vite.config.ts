import vue from '@vitejs/plugin-vue'
import { defineConfig, type UserConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 18421,
    strictPort: true,
  },
  test: {
    globals: true,
    environment: 'happy-dom',
  },
} as UserConfig)