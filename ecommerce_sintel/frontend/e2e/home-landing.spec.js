import { test, expect } from '@playwright/test';

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 1000 },
];

test.describe('Landing publica', () => {
  for (const viewport of viewports) {
    test(`${viewport.name}: estructura y ancho sin overflow`, async ({ page }) => {
      await page.setViewportSize(viewport);
      const consoleErrors = [];
      page.on('console', (message) => {
        if (message.type() === 'error') consoleErrors.push(message.text());
      });

      await page.goto('/');
      await expect(page.locator('.customer-navbar')).toBeVisible();
      await expect(page.locator('.home-root')).toBeVisible();
      await expect(page.locator('.customer-footer')).toBeVisible();

      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(consoleErrors).toEqual([]);
    });
  }
});
