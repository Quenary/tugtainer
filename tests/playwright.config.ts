import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL ?? 'http://localhost:9412';

export default defineConfig({
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'integration',
      testDir: './integration',
    },
    {
      name: 'e2e',
      testDir: './e2e',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
