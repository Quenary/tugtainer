import { test, expect } from '@playwright/test';

test('app loads and shows auth', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Tugtainer/i);
  await expect(page).toHaveURL(/\/auth/);
  await expect(page.locator('app-auth')).toBeVisible();
});
