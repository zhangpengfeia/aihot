import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 与生产 Nginx 一致：前端与接口同源，凭证仅存于服务端。
const proxy = Object.fromEntries(
  ['/api', '/docs', '/openapi.json'].map((path) => [path, 'http://127.0.0.1:8000']),
);
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', proxy },
  preview: { proxy },
});
