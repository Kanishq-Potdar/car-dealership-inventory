import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e', workers: 1, fullyParallel: false, retries: 0,
  use: { channel: 'chromium', baseURL: 'http://127.0.0.1:5174', viewport: { width: 1440, height: 1000 } },
  webServer: [
    { command: `"${process.env.E2E_PYTHON}" -B e2e/api_server.py`, url: 'http://127.0.0.1:8011/health', reuseExistingServer: false, timeout: 30000 },
    { command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort', url: 'http://127.0.0.1:5174', env: { API_TARGET: 'http://127.0.0.1:8011' }, reuseExistingServer: false },
  ],
})
