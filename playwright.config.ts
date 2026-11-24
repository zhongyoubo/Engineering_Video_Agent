import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';

const baseURL = `http://127.0.0.1:${process.env.EXPLAINER_DEV_PORT || 5173}`;
const python = resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');

export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  timeout: 90000,
  use: {
    baseURL,
    viewport: { width: 1440, height: 1080 },
    launchOptions: {
      executablePath: process.env.CHROME_EXECUTABLE || undefined,
      args: ['--no-sandbox'],
    },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `"${python}" scripts/dev.py`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 60000,
    env: {
      EXPLAINER_DATA_DIR: process.env.EXPLAINER_TEST_DATA_DIR || '.test-data',
      EXPLAINER_ALLOWED_ORIGINS: baseURL,
      EXPLAINER_API_TOKEN: 'e2e-only-not-a-production-key-123456',
      EXPLAINER_TENANT_KEYS: JSON.stringify({
        'e2e-second': 'e2e-second-tenant-only-test-key-123456',
      }),
      EXPLAINER_ENABLE_SANDBOX: 'false',
      EXPLAINER_ALLOW_EXTERNAL_MODEL: 'false',
    },
  },
});
