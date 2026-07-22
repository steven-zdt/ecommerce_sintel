import { chromium } from 'playwright';

const SCRATCHPAD = 'C:/Users/ADMINI~1/AppData/Local/Temp/claude/c--Users-Administrator-Documents-ecommerce-sintel-rest/8f2447f3-f37c-4df4-a8f1-6701d36e9951/scratchpad';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.setViewportSize({ width: 1440, height: 900 });

await page.goto('http://localhost:5173/alquiler/equipo/', { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
await page.screenshot({ path: SCRATCHPAD + '/01_alquiler_equipo_list.png', fullPage: true });
console.log('01: alquiler/equipo/ captured');

const rentalLinks = await page.evaluate(() =>
  Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('alquiler') && !h.endsWith('/alquiler/equipo/') && !h.endsWith('/alquiler/'))
);
console.log('Rental deep links:', JSON.stringify(rentalLinks.slice(0, 5)));

if (rentalLinks.length > 0) {
  await page.goto(rentalLinks[0], { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: SCRATCHPAD + '/02_alquiler_equipo_wizard_step1.png', fullPage: true });
  console.log('02: wizard step 1 captured at', rentalLinks[0]);

  const nextBtns = await page.locator('button').allTextContents();
  console.log('Buttons on page:', JSON.stringify(nextBtns));

  const nextBtn = page.locator('button').filter({ hasText: /Siguiente|Continuar|Solicitar/i }).first();
  if (await nextBtn.count() > 0) {
    await nextBtn.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: SCRATCHPAD + '/03_alquiler_wizard_step2.png', fullPage: true });
    console.log('03: wizard step 2 captured');

    const nextBtn2 = page.locator('button').filter({ hasText: /Siguiente|Continuar/i }).first();
    if (await nextBtn2.count() > 0) {
      await nextBtn2.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: SCRATCHPAD + '/04_alquiler_wizard_step3.png', fullPage: true });
      console.log('04: wizard step 3 captured');

      const nextBtn3 = page.locator('button').filter({ hasText: /Siguiente|Continuar/i }).first();
      if (await nextBtn3.count() > 0) {
        await nextBtn3.click();
        await page.waitForTimeout(1500);
        await page.screenshot({ path: SCRATCHPAD + '/04b_alquiler_wizard_step4.png', fullPage: true });
        console.log('04b: wizard step 4 captured');
      }
    }
  }
}

await page.goto('http://localhost:5173/servicios/', { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
await page.screenshot({ path: SCRATCHPAD + '/05_servicios_catalog.png', fullPage: true });
console.log('05: servicios/ catalog captured');

const serviceLinks = await page.evaluate(() =>
  Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('/servicios/') && !h.endsWith('/servicios/'))
);
console.log('Service detail links:', JSON.stringify(serviceLinks.slice(0, 5)));

if (serviceLinks.length > 0) {
  await page.goto(serviceLinks[0], { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: SCRATCHPAD + '/06_servicio_detail.png', fullPage: true });
  console.log('06: service detail captured at', serviceLinks[0]);

  const reqBtns = await page.locator('a, button').allTextContents();
  console.log('All btns/links:', JSON.stringify(reqBtns.slice(0, 20)));

  const requestBtn = page.locator('a, button').filter({ hasText: /Solicitar|Contratar|Reservar/i }).first();
  if (await requestBtn.count() > 0) {
    await requestBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: SCRATCHPAD + '/07_servicio_wizard_step1.png', fullPage: true });
    console.log('07: service wizard step 1 captured');

    const nextBtn = page.locator('button').filter({ hasText: /Siguiente|Continuar/i }).first();
    if (await nextBtn.count() > 0) {
      await nextBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: SCRATCHPAD + '/08_servicio_wizard_step2.png', fullPage: true });
      console.log('08: service wizard step 2 captured');

      const nextBtn2 = page.locator('button').filter({ hasText: /Siguiente|Continuar/i }).first();
      if (await nextBtn2.count() > 0) {
        await nextBtn2.click();
        await page.waitForTimeout(1500);
        await page.screenshot({ path: SCRATCHPAD + '/09_servicio_wizard_step3.png', fullPage: true });
        console.log('09: service wizard step 3 captured');

        const nextBtn3 = page.locator('button').filter({ hasText: /Siguiente|Continuar/i }).first();
        if (await nextBtn3.count() > 0) {
          await nextBtn3.click();
          await page.waitForTimeout(1500);
          await page.screenshot({ path: SCRATCHPAD + '/10_servicio_wizard_step4.png', fullPage: true });
          console.log('10: service wizard step 4 captured');
        }
      }
    }
  }
}

await browser.close();
console.log('All screenshots done!');
