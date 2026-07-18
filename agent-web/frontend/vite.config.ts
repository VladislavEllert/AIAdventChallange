import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1', // Node 22+/26 DNS ordering can resolve 'localhost' to ::1 only,
    // which breaks Playwright's webServer health check against 127.0.0.1.
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../agent_web/static',
    emptyOutDir: true,
  },
})
