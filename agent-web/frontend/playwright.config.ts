import { defineConfig, devices } from '@playwright/test'

// Phase E (week-07 dev-assistant plan): browser self-test infrastructure.
// Every later phase drives this suite before claiming a UI-touching task
// "done" — see .claude/skills/e2e-web/SKILL.md.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'e2e-report', open: 'never' }]],
  outputDir: 'e2e-results',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Both dev servers. reuseExistingServer:true means a server already running
  // locally (the common case while developing) is reused as-is, never killed —
  // no bash/lsof script needed to avoid testing a stale zombie process.
  webServer: [
    {
      command: './.venv/bin/python __main__.py',
      cwd: '..',
      url: 'http://127.0.0.1:8765/api/health',
      reuseExistingServer: true,
      timeout: 30_000,
      env: { AGENT_WEB_OPEN_BROWSER: '0' },
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
})
