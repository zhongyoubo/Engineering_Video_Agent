import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  timeout: 90000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    viewport: { width: 1440, height: 1080 },
    launchOptions: {
      executablePath: process.env.CHROME_EXECUTABLE || undefined,
      args: ['--no-sandbox'],
    },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: '.venv/bin/python scripts/dev.py',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    timeout: 60000,
    env: {
      EXPLAINER_DATA_DIR: '.test-data',
      EXPLAINER_API_TOKEN: 'e2e-only-not-a-production-key-123456',
      EXPLAINER_TENANT_KEYS: JSON.stringify({
        'e2e-second': 'e2e-second-tenant-only-test-key-123456',
      }),
      EXPLAINER_ENABLE_SANDBOX: 'false',
      EXPLAINER_ALLOW_EXTERNAL_MODEL: 'false',
    },
  },
});
