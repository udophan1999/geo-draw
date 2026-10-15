import { defineConfig, devices } from '@playwright/test'

// UI tests against the real API on a throwaway data folder with a fake AI (e2e/server.py),
// served by Vite in dev mode. Run from web/: `npm run test:e2e` (first time:
// `npx playwright install chromium`). Needs the repo's .venv (see CLAUDE.md).
// E2E_API_PORT / E2E_WEB_PORT let a second run go next to an open `npm run test:e2e:ui`.
const API_PORT = Number(process.env.E2E_API_PORT ?? 8765)
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 5174)

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    locale: 'vi-VN',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
    // Safari's engine: touch and focus behave differently from Chrome's.
    { name: 'iphone', use: { ...devices['iPhone 13'] } },
  ],
  webServer: [
    {
      command: `../.venv/bin/python e2e/server.py ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: false,
      stdout: 'ignore',
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { GEO_DRAW_API_PORT: String(API_PORT) },
      reuseExistingServer: !process.env.CI,
    },
  ],
})
