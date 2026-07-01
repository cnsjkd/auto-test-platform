import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '');
  const apiTarget = env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000';
  const wsTarget = apiTarget.replace(/^http/, 'ws');

  return {
    envDir: '..',
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: wsTarget,
          ws: true,
        },
      },
    },
  };
});
