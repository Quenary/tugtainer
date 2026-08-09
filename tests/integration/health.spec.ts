import { test, expect } from '@playwright/test';

test('health endpoint is ok', async ({ request }) => {
  const response = await request.get('/api/public/health');
  expect(response.ok()).toBeTruthy();
});
