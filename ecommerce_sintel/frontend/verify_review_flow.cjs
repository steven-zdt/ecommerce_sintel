const { chromium } = require('playwright');

const EQUIPMENT_UUID = '693e2d7e-b260-4206-9058-4566b08e4e6a';

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage({ viewport: { width: 1300, height: 1000 } });
  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'review_customer@example.com');
  await page.fill('input[type="password"]', 'DevTest12345!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);
  console.log('After login URL:', page.url());

  await page.goto(`http://localhost:5173/alquiler/equipo/${EQUIPMENT_UUID}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  const reviewSection = page.locator('.eq-review-form');
  await reviewSection.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/tmp/review_form_before.png' });

  // Seleccionar 5 estrellas
  const stars = page.locator('.eq-star-btn');
  await stars.nth(4).click();
  await page.fill('.eq-review-textarea', 'Excelente equipo, entrega puntual y en perfectas condiciones. Muy recomendado.');
  await page.click('.eq-review-submit');
  await page.waitForTimeout(1500);

  await page.screenshot({ path: '/tmp/review_form_after.png' });

  const reviewCount = await page.locator('.eq-review-item').count();
  const summaryText = await page.locator('.eq-reviews-score strong').first().textContent();
  console.log('Review items after submit:', reviewCount);
  console.log('Average score shown:', summaryText);
  console.log('Console errors:', consoleErrors.length ? consoleErrors : 'NONE');

  await browser.close();
})().catch((err) => { console.error('FATAL', err); process.exit(1); });
