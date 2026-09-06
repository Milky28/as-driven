const { test, expect } = require('@playwright/test');

const mclaren = '#car-mclaren-720s-gt3-evo';

test('visible car stripes survive search, simulator filters and an expanded detail', async ({ page }) => {
  await page.goto('/');
  const checkStripes = async () => {
    const stripes = await page.locator('tr.car:visible').evaluateAll(rows =>
      rows.map(row => row.classList.contains('row-alternate')));
    expect(stripes.length).toBeGreaterThan(1);
    expect(stripes).toEqual(stripes.map((_, index) => index % 2 === 1));
  };
  await checkStripes();
  await page.locator('#q').fill('BMW');
  await checkStripes();
  await page.locator('#f-simulator').selectOption('ams2');
  await checkStripes();
  const first = page.locator('tr.car:visible').first();
  await first.press('Enter');
  await expect(first).toHaveAttribute('aria-expanded', 'true');
  await expect(first.locator('xpath=following-sibling::tr[1]')).toBeVisible();
  await checkStripes();
});

test('light, dark and system themes preserve distinct rows and the selected detail', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/#mclaren-720s-gt3-evo--acc');
  for (const choice of ['light', 'dark', 'system']) {
    await page.locator(`[data-theme-set="${choice}"]`).click();
    const backgrounds = await page.locator('tr.car:visible').evaluateAll(rows =>
      rows.slice(0, 2).map(row => getComputedStyle(row).backgroundColor));
    expect(backgrounds[0]).not.toBe(backgrounds[1]);
    await expect(page.locator(mclaren)).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator(`[data-theme-set="${choice}"]`)).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('body')).toHaveCSS('background-color', choice === 'light'
      ? 'rgb(232, 237, 242)' : 'rgb(16, 25, 35)');
  }
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(232, 237, 242)');
});

test('populated mobile cards and expanded guidance fit the viewport', async ({ page }) => {
  for (const width of [360, 736, 1024]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto('/');
    expect(await page.locator('html').evaluate(root => root.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.goto('/#mclaren-720s-gt3-evo--acc');
    await expect(page.locator(mclaren)).toBeVisible();
    expect(await page.locator('html').evaluate(root => root.scrollWidth <= window.innerWidth)).toBeTruthy();
  }
});

test('a selected simulator view stays visible when another filter conflicts', async ({ page }) => {
  await page.goto('/#mclaren-720s-gt3-evo--acc');
  await expect(page.locator(mclaren)).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#mclaren-720s-gt3-evo--acc-tab')).toHaveAttribute('aria-selected', 'true');

  await page.locator('#f-actuation').selectOption('h-pattern');
  await expect(page.locator(mclaren)).toBeVisible();
  await expect(page.locator(mclaren).locator('xpath=following-sibling::tr[1]')).toBeVisible();
  await expect(page.locator('#filter-note')).toContainText('Selected car remains open');
  await expect(page.locator('#results-status')).toContainText('Selected car remains open');
});

test('simulator tabs work with keyboard navigation and update the simulator filter', async ({ page }) => {
  await page.goto('/#mclaren-720s-gt3-evo--acc');
  const accTab = page.locator('#mclaren-720s-gt3-evo--acc-tab');
  await accTab.focus();
  await page.keyboard.press('ArrowRight');

  await expect(page.locator('#mclaren-720s-gt3-evo--ams2-tab')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#f-simulator')).toHaveValue('ams2');
});

test('search announces an empty result set and the catalog does not overflow a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto('/');
  await page.locator('#q').fill('not-a-real-as-driven-car');

  await expect(page.locator('#empty')).toBeVisible();
  await expect(page.locator('#results-status')).toContainText('0 of');
  expect(await page.locator('html').evaluate(
    (root) => root.scrollWidth <= window.innerWidth,
  )).toBeTruthy();
});

test('active filters are named and can be cleared without hiding a selected detail', async ({ page }) => {
  await page.goto('/#mclaren-720s-gt3-evo--acc');
  await page.locator('#f-actuation').selectOption('h-pattern');
  await expect(page.locator('#active-filters')).toBeVisible();
  await expect(page.locator('#filter-chips')).toContainText('Shifter: H-pattern');

  await page.locator('#clear-filters').click();
  await expect(page.locator('#active-filters')).toBeHidden();
  await expect(page.locator(mclaren)).toHaveAttribute('aria-expanded', 'true');
});

test('the results context distinguishes the real-car baseline from simulator guidance', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#table-context')).toContainText('Real-car baseline');

  await page.locator('#f-simulator').selectOption('ams2');
  await expect(page.locator('#table-context')).toContainText('Driving in AMS2');
  await expect(page.locator('#table-context')).toContainText('separately from the real-car baseline');
});

test('driver lookup leads the page and research mode keeps the focus on its own content', async ({ page }) => {
  await page.goto('/');

  const lookup = page.locator('#lookup-controls');
  const coverage = page.locator('.coverage');
  expect((await lookup.boundingBox()).y).toBeLessThan((await coverage.boundingBox()).y);

  await page.getByRole('button', { name: 'Research findings' }).click();
  await expect(lookup).toBeHidden();
  await expect(page.locator('#benchmark-view')).toBeVisible();
});
