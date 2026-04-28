import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import path from 'node:path';

const samplePdfPath = path.resolve(process.cwd(), '../backend/samples/plan.pdf');

interface PreviewPayload {
  sessionId: string;
}

async function uploadReferencePlan(page: Page): Promise<PreviewPayload> {
  await page.goto('/');

  const previewResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/api/preview') && response.request().method() === 'POST',
  );
  await page.locator('input[type="file"]').setInputFiles(samplePdfPath);
  const preview = (await (await previewResponsePromise).json()) as PreviewPayload;

  await expect(page.getByText('Wgrano plan.pdf')).toBeVisible();
  await expect(page.getByTestId('canvas-surface')).toBeVisible();

  return preview;
}

async function analyzeReferencePlan(page: Page): Promise<string> {
  await page.getByRole('button', { name: 'Analizuj plan' }).click();
  await expect(page.getByText('Analiza gotowa. Wykryto 134 boxów.')).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText('Suma wszystkich symboli: 134 szt.')).toBeVisible();

  const analysisText = await page.getByTestId('analysis-id').innerText();
  return analysisText.replace('Analiza ', '').trim();
}

function legendNumberFromSymbolName(symbolName: string): string | null {
  return symbolName.match(/^(\d{1,3})(?:_|-|$)/)?.[1] ?? null;
}

async function templateNumberForSymbol(page: Page, symbolName: string): Promise<string> {
  const number = await page.getByTestId('template-card').evaluateAll((cards, expectedName) => {
    const card = cards.find((item) => item.querySelector('[data-testid="template-symbol-name"]')?.textContent?.trim() === expectedName);
    return card?.querySelector('[data-testid="template-symbol-number"]')?.textContent?.trim() ?? null;
  }, symbolName);
  if (!number) {
    throw new Error(`Missing template number for ${symbolName}`);
  }
  return number;
}

test('uploads reference plan, navigates canvas, extracts legend, and analyzes 134 boxes', async ({ page }) => {
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
  await uploadReferencePlan(page);

  const scroll = page.getByTestId('canvas-scroll');
  const surface = page.getByTestId('canvas-surface');
  const beforePan = await scroll.evaluate((element) => ({
    left: element.scrollLeft,
    top: element.scrollTop,
  }));
  const surfaceBox = await surface.boundingBox();
  expect(surfaceBox).not.toBeNull();
  if (!surfaceBox) {
    return;
  }

  await page.mouse.move(surfaceBox.x + 420, surfaceBox.y + 300);
  await page.mouse.down();
  await page.mouse.move(surfaceBox.x + 260, surfaceBox.y + 180);
  await page.mouse.up();

  const afterPan = await scroll.evaluate((element) => ({
    left: element.scrollLeft,
    top: element.scrollTop,
  }));
  expect(afterPan.left + afterPan.top).toBeGreaterThan(beforePan.left + beforePan.top);

  await page.getByRole('button', { name: 'Powiększ' }).click();
  await expect(page.getByText('44%')).toBeVisible();
  await page.getByRole('button', { name: 'Dopasuj do widoku' }).click();

  await page.getByRole('button', { name: 'Wyodrębnij legendę' }).click();
  await expect(page.getByText('Wyodrębniono 22 wzorców.')).toBeVisible();
  await expect(page.getByTestId('template-symbol-number').first()).toHaveText('01');
  await expect(page.getByTestId('template-symbol-number').nth(21)).toHaveText('22');

  await analyzeReferencePlan(page);
  const firstLegendName = await page.getByTestId('legend-symbol-name').first().innerText();
  const firstLegendNumber = legendNumberFromSymbolName(firstLegendName) ?? await templateNumberForSymbol(page, firstLegendName);
  await expect(page.getByTestId('legend-symbol-number').first()).toHaveText(firstLegendNumber);
  await expect(page.getByTestId('canvas-symbol-number')).toHaveCount(134);
  await expect(page.getByRole('button', { name: 'Wykryte' })).toBeVisible();
  await page.getByRole('button', { name: 'Wykryte' }).click();
  const firstDetectionName = await page.getByTestId('detection-symbol-name').first().innerText();
  const firstDetectionNumber = legendNumberFromSymbolName(firstDetectionName) ?? await templateNumberForSymbol(page, firstDetectionName);
  await expect(page.getByTestId('detection-symbol-number').first()).toHaveText(firstDetectionNumber);
  await expect(page.getByTestId('canvas-symbol-number').first()).toHaveText(firstDetectionNumber);

  await page.getByTestId('canvas-detection-box').first().click({ force: true });
  await expect(page.getByText(/Skopiowano log boxa/)).toBeVisible();

  const copiedText = await page.evaluate(() => navigator.clipboard.readText());
  const copied = JSON.parse(copiedText) as {
    type: string;
    legendNumber: string | null;
    referenceJsonCandidate: { symbolName: string; x: number; y: number; width: number; height: number };
  };
  expect(copied.type).toBe('elektroscan_detection_box_log');
  expect(copied.legendNumber).toBe(firstDetectionNumber);
  expect(copied.referenceJsonCandidate.symbolName).toBe(firstDetectionName);
  expect(typeof copied.referenceJsonCandidate.x).toBe('number');
  expect(typeof copied.referenceJsonCandidate.y).toBe('number');
  expect(typeof copied.referenceJsonCandidate.width).toBe('number');
  expect(typeof copied.referenceJsonCandidate.height).toBe('number');
});

test('supports canvas navigation on narrow viewport without page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await uploadReferencePlan(page);

  const pageOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(pageOverflow).toBeLessThanOrEqual(1);

  const scroll = page.getByTestId('canvas-scroll');
  await scroll.scrollIntoViewIfNeeded();
  const beforePan = await scroll.evaluate((element) => ({
    left: element.scrollLeft,
    top: element.scrollTop,
  }));
  const scrollBox = await scroll.boundingBox();
  expect(scrollBox).not.toBeNull();
  if (!scrollBox) {
    return;
  }

  await page.mouse.move(scrollBox.x + scrollBox.width * 0.72, scrollBox.y + scrollBox.height * 0.62);
  await page.mouse.down();
  await page.mouse.move(scrollBox.x + scrollBox.width * 0.28, scrollBox.y + scrollBox.height * 0.36);
  await page.mouse.up();

  const afterPan = await scroll.evaluate((element) => ({
    left: element.scrollLeft,
    top: element.scrollTop,
  }));
  expect(afterPan.left + afterPan.top).toBeGreaterThan(beforePan.left + beforePan.top);

  await page.getByRole('button', { name: 'Powiększ' }).click();
  await expect(page.getByText('44%')).toBeVisible();
});

test('recovers from failed upload by retrying the stored PDF', async ({ page }) => {
  let previewCalls = 0;
  await page.route('**/api/preview', async (route) => {
    previewCalls += 1;
    if (previewCalls === 1) {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Backend chwilowo niedostępny.' }),
      });
      return;
    }
    await route.continue();
  });

  await page.goto('/');
  await page.locator('input[type="file"]').setInputFiles(samplePdfPath);
  await expect(page.getByText('Backend chwilowo niedostępny.')).toBeVisible();
  await expect(page.getByTestId('status-retry')).toBeVisible();

  await page.getByTestId('status-retry').click();
  await expect(page.getByText('Wgrano plan.pdf')).toBeVisible();
  await expect(page.getByTestId('canvas-surface')).toBeVisible();
  expect(previewCalls).toBe(2);
});

test('recovers from failed analysis by retrying the same session', async ({ page }) => {
  await uploadReferencePlan(page);

  let analyzeCalls = 0;
  await page.route('**/api/analyze?**', async (route) => {
    analyzeCalls += 1;
    if (analyzeCalls === 1) {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Analiza chwilowo niedostępna.' }),
      });
      return;
    }
    await route.continue();
  });

  await page.getByRole('button', { name: 'Analizuj plan' }).click();
  await expect(page.getByText('Analiza chwilowo niedostępna.')).toBeVisible();
  await expect(page.getByTestId('status-retry')).toBeVisible();

  await page.getByTestId('status-retry').click();
  await expect(page.getByText('Analiza gotowa. Wykryto 134 boxów.')).toBeVisible({ timeout: 120_000 });
  expect(analyzeCalls).toBe(2);
});

test('shows template lifecycle states for extract, rename, delete, and clear', async ({ page }) => {
  await uploadReferencePlan(page);
  await expect(page.getByTestId('template-count')).toHaveText('0 wzorców');
  await expect(page.getByTestId('template-state')).toContainText('Brak wzorców');

  await page.getByRole('button', { name: 'Wyodrębnij legendę' }).click();
  await expect(page.getByText('Wyodrębniono 22 wzorców.')).toBeVisible();
  await expect(page.getByTestId('template-count')).toHaveText('22 wzorce');
  await expect(page.getByTestId('template-card')).toHaveCount(22);
  await expect(page.getByTestId('template-state')).toContainText('Wzorce gotowe do analizy');

  page.once('dialog', async (dialog) => {
    await dialog.accept('e2e_renamed_symbol');
  });
  await page.getByTestId('template-rename').first().click();
  await expect(page.getByText('Zmieniono nazwę wzorca: e2e_renamed_symbol.')).toBeVisible();
  await expect(page.getByTestId('template-card').filter({ hasText: 'e2e_renamed_symbol' })).toBeVisible();

  await page.getByTestId('template-delete').first().click();
  await expect(page.getByText(/Usunięto wzorzec:/)).toBeVisible();
  await expect(page.getByTestId('template-count')).toHaveText('21 wzorców');
  await expect(page.getByTestId('template-card')).toHaveCount(21);

  await page.getByRole('button', { name: 'Wyczyść wzorce' }).click();
  await expect(page.getByText('Wyczyszczono bazę wzorców.')).toBeVisible();
  await expect(page.getByTestId('template-count')).toHaveText('0 wzorców');
  await expect(page.getByTestId('template-state')).toContainText('Brak wzorców');
});

test('stores review state in localStorage scoped by session and analysis', async ({ page }) => {
  const preview = await uploadReferencePlan(page);
  const analysisId = await analyzeReferencePlan(page);
  const boxStatusesKey = `elektroscan:${preview.sessionId}:${analysisId}:boxStatuses`;
  const hiddenSymbolTypesKey = `elektroscan:${preview.sessionId}:${analysisId}:hiddenSymbolTypes`;

  await page.getByTestId('legend-hide-toggle').first().click();
  await page.getByRole('button', { name: 'Wykryte' }).click();
  await page.getByTestId('detection-confirm').first().click();

  await expect
    .poll(() =>
      page.evaluate((key) => {
        const value = localStorage.getItem(key);
        return value ? Object.values(JSON.parse(value)).includes('confirmed') : false;
      }, boxStatusesKey),
    )
    .toBe(true);

  await expect
    .poll(() =>
      page.evaluate((key) => {
        const value = localStorage.getItem(key);
        return value ? Object.values(JSON.parse(value)).includes(true) : false;
      }, hiddenSymbolTypesKey),
    )
    .toBe(true);

  const storageKeys = await page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith('elektroscan:')));
  expect(storageKeys).toContain(boxStatusesKey);
  expect(storageKeys).toContain(hiddenSymbolTypesKey);
  expect(storageKeys.some((key) => key === 'boxStatuses' || key === 'hiddenSymbolTypes')).toBe(false);
});

test('reviews detections in slideshow with keyboard and mouse controls', async ({ page }) => {
  await uploadReferencePlan(page);
  await analyzeReferencePlan(page);

  await page.getByTestId('legend-start-slideshow').first().click();
  await expect(page.getByTestId('slideshow-overlay')).toBeVisible();
  await expect(page.getByTestId('slideshow-counter')).toContainText('1/');

  await page.keyboard.press('KeyY');
  await expect(page.getByTestId('slideshow-counter')).toContainText('2/');

  await page.getByTestId('slideshow-reject').click();
  await expect(page.getByTestId('slideshow-counter')).toContainText('3/');

  await page.keyboard.press('Escape');
  await expect(page.getByTestId('slideshow-overlay')).toBeHidden();
});
