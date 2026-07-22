const { chromium } = require('playwright');

const EQUIPMENT_UUID = '693e2d7e-b260-4206-9058-4566b08e4e6a';

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  // Login
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'review_customer@example.com');
  await page.fill('input[type="password"]', 'DevTest12345!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  // Detail page hero
  await page.goto(`http://localhost:5173/alquiler/equipo/${EQUIPMENT_UUID}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: '/tmp/refactor_detail_hero.png' });

  const trustGridCount = await page.locator('.trust-grid > div').count();
  const packageCardCount = await page.locator('.package-card').count();
  const valueGridCount = await page.locator('.value-grid article').count();
  const shareBtn = await page.locator('.icon-action-btn').count();
  console.log('trust-grid items:', trustGridCount);
  console.log('package-card count:', packageCardCount);
  console.log('value-grid items:', valueGridCount);
  console.log('share/fav buttons:', shareBtn);

  // Toggle favorite
  await page.locator('.icon-action-btn').nth(1).click();
  await page.waitForTimeout(300);
  const favActive = await page.locator('.icon-action-btn.active').count();
  console.log('favorite active after click:', favActive);

  // Scroll to spec table, toggle collapse
  const specGroupHead = page.locator('.eq-spec-group-head').first();
  if (await specGroupHead.count()) {
    await specGroupHead.scrollIntoViewIfNeeded();
    await page.screenshot({ path: '/tmp/refactor_spec_table.png' });
    await specGroupHead.click();
    await page.waitForTimeout(300);
  }

  // Video modal
  const videoThumb = page.locator('.eq-video-thumb').first();
  if (await videoThumb.count()) {
    await videoThumb.scrollIntoViewIfNeeded();
    await videoThumb.click();
    await page.waitForTimeout(500);
    const modalVisible = await page.locator('.eq-video-modal').isVisible();
    console.log('video modal visible:', modalVisible);
    await page.screenshot({ path: '/tmp/refactor_video_modal.png' });
    await page.locator('.eq-video-modal .btn-close').click();
    await page.waitForTimeout(300);
  }

  // Go to booking wizard
  await page.goto(`http://localhost:5173/alquiler/equipo/${EQUIPMENT_UUID}/solicitar`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: '/tmp/refactor_wizard_step1.png' });

  const fillWidth = await page.locator('.steps-fill').evaluate((el) => el.style.width).catch(() => null);
  console.log('steps-fill width at step1:', fillWidth);

  console.log('Console errors:', consoleErrors.length ? consoleErrors : 'NONE');
  await browser.close();
})().catch((err) => { console.error('FATAL', err); process.exit(1); });
