import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // port dan alamat backend bisa diganti lewat frontend/.env.local
  const env = loadEnv(mode, process.cwd(), '')
  const api = env.VITE_API_TARGET || 'http://localhost:8000'

  return {
    plugins: [vue(), vueDevTools()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: Number(env.WEB_PORT || 5173),
      strictPort: true,
      // /api diteruskan ke FastAPI sehingga cookie sesi tetap satu origin seperti di Vercel
      proxy: {
        '/api': api,
        '/docs': api,
        '/openapi.json': api,
      },
    },
  }
})
