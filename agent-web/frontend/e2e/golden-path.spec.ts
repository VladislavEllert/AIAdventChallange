import { test, expect } from '@playwright/test'

// Guards the golden path: open chat, send a message, get a real (non-empty)
// assistant response, and the input must be usable again afterward.
//
// This directly targets a past regression class — "send button/input stuck
// disabled forever after a response" (see memory note "Drive golden path").
// A pure API/curl check can't catch that bug: it only shows up as frontend
// state that never resets after the SSE stream ends.
//
// Uses a live ProxyAPI call (openai/gpt-4o-mini) switched in via /model —
// the store's default model is ollama/qwen3:4b, which isn't reachable from
// this dev machine. Requires PROXYAPI_KEY in the repo-root/.venv-visible
// .env (see agent-cli/agent_cli/config.py two-pass dotenv load). If the key
// is missing/invalid the assistant bubble will show an error instead of a
// real answer and this test fails loudly rather than silently passing.
test('golden path: send a message, get a non-empty reply, input re-enables', async ({ page }) => {
  await page.goto('/')

  // First-run nickname modal — no auth, just tags sessions with a name.
  // Fresh browser context (Playwright's default) always starts with empty
  // localStorage, so this always shows; wait for it explicitly rather than
  // a non-waiting isVisible() check.
  const nicknameInput = page.getByPlaceholder('Например: Влад')
  await nicknameInput.waitFor({ state: 'visible', timeout: 5_000 })
  await nicknameInput.fill('e2e-bot')
  await page.getByRole('button', { name: 'Продолжить' }).click()
  await nicknameInput.waitFor({ state: 'hidden', timeout: 5_000 })

  // New chat session.
  await page.getByRole('button', { name: /Новый чат/ }).click()

  const textarea = page.getByPlaceholder(/Напиши сообщение/)
  await expect(textarea).toBeVisible()

  // Switch off the unreachable local default model onto the cloud one via
  // the existing /model slash command (client-side only, no settings.json
  // edit — that belongs to phase 0, not this infra phase).
  await textarea.fill('/model openai/gpt-4o-mini')
  await textarea.press('Enter')
  await expect(page.getByText('Модель переключена')).toBeVisible()

  // Send a real message.
  await textarea.fill('Скажи одно слово: тест')
  await expect(textarea).toBeEnabled()
  await textarea.press('Enter')

  // Input disables while streaming...
  await expect(textarea).toBeDisabled()

  // ...and a non-empty assistant reply shows up.
  const assistantBubble = page.locator('.prose').last()
  await expect(assistantBubble).not.toHaveText('', { timeout: 30_000 })

  // Regression guard: input must be enabled again once streaming ends, not
  // stuck disabled forever.
  await expect(textarea).toBeEnabled({ timeout: 10_000 })
  await expect(textarea).toHaveAttribute('placeholder', /Напиши сообщение/)
})
