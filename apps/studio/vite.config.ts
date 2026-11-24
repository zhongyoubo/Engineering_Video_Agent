import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [react()],
  publicDir: fileURLToPath(new URL('../../assets', import.meta.url)),
  server: {
    host: '127.0.0.1',
    port: Number(process.env.EXPLAINER_DEV_PORT || 5173),
    fs: { allow: [fileURLToPath(new URL('../..', import.meta.url))] },
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${process.env.EXPLAINER_DEV_API_PORT || 8000}`,
        changeOrigin: true,
      },
    },
  },
});
