import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: '/2gis_app/', // ⚠️ ВАЖНО: имя вашего репозитория
})