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
      testIgnore: '**/swarm-schedule.spec.ts',
    },
    {
      // Global check/update touches every container on the engine, so this
      // file stays out of the parallel integration project.
      name: 'swarm-schedule',
      testDir: './integration',
      testMatch: '**/swarm-schedule.spec.ts',
      dependencies: ['integration'],
    },
    {
      name: 'e2e',
      testDir: './e2e',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      // Replaces the app container, so it runs after everything else
      name: 'self-update',
      testDir: './self-update',
      dependencies: ['integration', 'e2e', 'swarm-schedule'],
      retries: 0,
    },
  ],
});
