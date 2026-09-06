const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/browser',
  fullyParallel: true,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:4173', headless: true },
  webServer: {
    command: 'python -m as_driven_db build-site --output build/site/index.html && python -m http.server 4173 --directory build/site',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
  },
});
